"""关卡加载 + 会话状态（进度、当前容器）。

设计原则：
  * 一关 = levels/<id>/ 目录，里面自带 Dockerfile、任务文件、判题脚本
  * level.json 描述元数据，前端完全由它驱动渲染
  * 通关 -> 判题脚本退出码 0 -> 立刻销毁容器 -> 进度 +1
  * 状态落盘到 .state/state.json，服务重启不丢
"""

import http.client
import json
import os
import random
import string
import threading
import time

from docker_ctl import (
    DockerError,
    connect_network,
    container_running,
    create_network,
    ensure_image,
    exec_capture,
    exec_detached,
    published_port,
    remove_container,
    remove_network,
    run_container,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS_DIR = os.path.join(ROOT, "levels")
STATE_DIR = os.path.join(ROOT, ".state")
STATE_FILE = os.path.join(STATE_DIR, "state.json")

DEFAULT_LEVEL = {
    "order": 999,
    "category": "unknown",
    "category_label": "未分类",
    "tool": "other",
    "tool_label": "其他",
    "platform_notes": {},
    "method": {},
    "vscode": False,
    "sidecars": [],
    "skippable": False,
    "skip_reason": "",
    "symptom": "",
    "diagnose": [],
    "solution": [],
    "title": "未命名关卡",
    "summary": "",
    "objectives": [],
    "hints": [],
    "workdir": "/work",
    "judge_timeout": 120,
}

LOCK = threading.RLock()


def _log(msg):
    print(f"[levels] {msg}", flush=True)


CHECK_PREFIX = "CHECK|"
RESULT_PREFIX = "RESULT|"


VSCODE_PORT = 8080


def _vscode_wait_ready(port, timeout=40):
    """等 code-server 起来（它的 /healthz 返回 200 就算就绪）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("GET", "/healthz")
            resp = conn.getresponse()
            resp.read()
            conn.close()
            if resp.status < 500:
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def _start_vscode(cid, level):
    """在容器里拉起 code-server，返回 {port, ready} 或 None。"""
    info = published_port(cid, VSCODE_PORT)
    if not info:
        return None
    _, host_port = info
    workdir = level["workdir"]
    cmd = (
        f"code-server --bind-addr 0.0.0.0:{VSCODE_PORT} --auth none "
        "--disable-telemetry --disable-update-check --disable-workspace-trust "
        "--disable-getting-started-override "
        f"--user-data-dir /tmp/code-data {workdir} "
        "> /tmp/code-server.log 2>&1"
    )
    try:
        exec_detached(cid, ["bash", "-lc", cmd])
    except DockerError:
        return {"port": host_port, "ready": False, "error": "code-server 启动失败"}
    ready = _vscode_wait_ready(host_port)
    return {"port": host_port, "ready": ready}


def parse_judge_output(text, exit_code):
    """判题脚本按行输出结构化结果：

        CHECK|ok|<名称>|<细节>
        CHECK|fail|<名称>|<细节>
        RESULT|pass 或 RESULT|fail

    没有 RESULT 行时退回用退出码判断（兼容老脚本）。
    """
    checks, plain, result = [], [], None
    for line in text.splitlines():
        if line.startswith(CHECK_PREFIX):
            parts = line.split("|", 3)
            if len(parts) >= 3:
                checks.append({
                    "status": parts[1].strip(),
                    "name": parts[2].strip(),
                    "detail": parts[3].strip() if len(parts) > 3 else "",
                })
        elif line.startswith(RESULT_PREFIX):
            result = line.split("|", 1)[1].strip()
        else:
            plain.append(line)
    if result in ("pass", "fail"):
        passed = result == "pass"
    else:
        passed = exit_code == 0
    return passed, checks, "\n".join(plain).strip()


class LevelStore:
    def __init__(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        self.levels = self._load_levels()
        self.state = self._load_state()

    # ---------------- 关卡 ----------------
    def _load_levels(self):
        levels = []
        if not os.path.isdir(LEVELS_DIR):
            return levels
        for name in sorted(os.listdir(LEVELS_DIR)):
            d = os.path.join(LEVELS_DIR, name)
            meta_path = os.path.join(d, "level.json")
            if not os.path.isfile(meta_path):
                continue
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta.setdefault("id", name)
            for k, v in DEFAULT_LEVEL.items():
                meta.setdefault(k, v)
            meta["dir"] = d
            meta["image"] = meta.get("image") or f"envtrainer/{meta['id']}:latest"
            meta["judge"] = os.path.join(d, meta.get("judge_script", "judge.sh"))
            levels.append(meta)
        levels.sort(key=lambda m: (m["order"], m["id"]))
        return levels

    def public_levels(self):
        out = []
        for m in self.levels:
            out.append({
                "id": m["id"],
                "order": m["order"],
                "title": m["title"],
                "summary": m["summary"],
                "objectives": m["objectives"],
                "hints": m["hints"],
                "workdir": m["workdir"],
                "category": m["category"],
                "category_label": m["category_label"],
                "tool": m["tool"],
                "tool_label": m["tool_label"],
                "vscode": bool(m.get("vscode")),
                "skippable": bool(m.get("skippable")),
                "platform_notes": m["platform_notes"],
                "method": m.get("method", {}),
                "points": m.get("points", 100),
            })
        return out

    def level_by_id(self, level_id):
        for m in self.levels:
            if m["id"] == level_id:
                return m
        return None

    def level_at(self, index):
        if 0 <= index < len(self.levels):
            return self.levels[index]
        return None

    # ---------------- 状态 ----------------
    def _load_state(self):
        if os.path.isfile(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    st = json.load(f)
            except Exception:
                st = {}
        else:
            st = {}
        st.setdefault("cursor", 0)
        st.setdefault("completed", [])
        st.setdefault("skipped", [])
        st.setdefault("session", None)
        st.setdefault("log", [])
        return st

    def save(self):
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)

    def note(self, text, kind="info"):
        entry = {"t": time.strftime("%H:%M:%S"), "kind": kind, "text": text}
        self.state["log"].append(entry)
        self.state["log"] = self.state["log"][-80:]
        self.save()
        return entry

    # ---------------- 会话 ----------------
    def current_level(self):
        lv = self.level_at(self.state["cursor"])
        return lv

    def session_info(self):
        s = self.state.get("session")
        if not s:
            return None
        alive = container_running(s["container"])
        if not alive:
            self.state["session"] = None
            self.save()
            return None
        return {
            "container": s["container"],
            "name": s["name"],
            "level_id": s["level_id"],
            "started": s["started"],
            "image": s.get("image"),
            "vscode": s.get("vscode"),
            "net": s.get("net"),
            "sidecars": s.get("sidecars") or [],
        }

    def _start_sidecars(self, level, sid):
        """给关卡拉起附属容器（比如代理），并建一个内部网络。"""
        sidecars = level.get("sidecars") or []
        if not sidecars:
            return None, []
        net = f"envtrainer-net-{sid}"
        create_network(net, internal=True)
        started = []
        for sc in sidecars:
            name = f"envtrainer-sc-{sid}-{sc['name']}"
            ctx = os.path.join(level["dir"], sc["context"]) if sc.get("context") else level["dir"]
            ensure_image(sc["image"], ctx, log=_log)
            cid = run_container(
                name=name,
                image=sc["image"],
                labels={"envtrainer.level": level["id"], "envtrainer.role": "sidecar"},
                workdir=sc.get("workdir", "/"),
                network=net,
                alias=sc["name"],
                command=sc.get("command"),
            )
            started.append({"name": name, "container": cid, "alias": sc["name"]})
            if sc.get("egress"):
                connect_network("bridge", cid)
            self.note(f"附属服务已启动 {sc['name']}", "up")
        return net, started

    def _new_container_name(self, level_id):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"envtrainer-{level_id.replace('.', '-')}-{suffix}"

    def start_session(self):
        """为当前关卡启动干净容器；已有容器先销毁。"""
        with LOCK:
            lv = self.current_level()
            if lv is None:
                raise DockerError("没有下一个关卡了，课程已全部完成")
            if not os.path.isfile(lv["judge"]):
                raise DockerError(f"关卡 {lv['id']} 缺少判题脚本 judge.sh")

            self.stop_session(reason="restart")

            ensure_image(lv["image"], lv["dir"], log=_log)

            name = self._new_container_name(lv["id"])
            sid = name.rsplit("-", 1)[-1]
            net, sidecars = self._start_sidecars(lv, sid)

            cid = run_container(
                name=name,
                image=lv["image"],
                labels={"envtrainer.level": lv["id"], "envtrainer.role": "challenge"},
                workdir=lv["workdir"],
                publish=f"127.0.0.1:0:{VSCODE_PORT}" if lv.get("vscode") else None,
                network=net,
            )
            self.state["session"] = {
                "container": cid,
                "name": name,
                "level_id": lv["id"],
                "started": time.time(),
                "image": lv["image"],
                "vscode": None,
                "net": net,
                "sidecars": sidecars,
            }
            self.note(f"容器已启动 {name}（关卡 {lv['id']}）", "up")

            if lv.get("vscode"):
                vs = _start_vscode(cid, lv)
                self.state["session"]["vscode"] = vs
                if vs and vs.get("ready"):
                    self.note(f"编辑器就绪（宿主端口 {vs['port']}）", "up")
                else:
                    self.note("编辑器启动较慢或失败，可用「重连终端」旁的按钮重试", "fail")
                self.save()
            return self.session_info()

    def stop_session(self, reason="manual"):
        s = self.state.get("session")
        if s:
            for sc in s.get("sidecars") or []:
                remove_container(sc["container"])
            remove_container(s["container"])
            remove_container(s["name"])
            if s.get("net"):
                remove_network(s["net"])
            self.note(f"容器已销毁 {s['name']}（{reason}）", "down")
        self.state["session"] = None
        self.save()

    def judge(self):
        """在容器里跑判题脚本。返回 {pass, output, level_id}"""
        with LOCK:
            lv = self.current_level()
            if lv is None:
                return {"pass": True, "output": "课程已全部完成", "finished": True}
            s = self.state.get("session")
            if not s or not container_running(s["container"]):
                raise DockerError("当前没有运行中的容器，请先点『开始/重开本关』")

            cp = exec_capture(
                s["container"],
                ["bash", "/opt/judge/judge.sh"],
                timeout=lv["judge_timeout"],
                workdir=lv["workdir"],
            )
            raw = (cp.stdout or "") + (cp.stderr or "")
            ok, checks, output = parse_judge_output(raw, cp.returncode)
            if not ok:
                failed = [c["name"] for c in checks if c["status"] != "ok"]
                self.note("判题未通过" + (f"（{len(failed)} 项未过）" if failed else f"（exit={cp.returncode}）"), "fail")
                return {
                    "pass": False,
                    "output": output[-8000:] if output else raw.strip()[-8000:],
                    "checks": checks,
                    "level_id": lv["id"],
                }

            # 通过：立刻销毁容器，推进进度
            passed_id = lv["id"]
            self.stop_session(reason=f"通关 {passed_id}")
            if passed_id not in self.state["completed"]:
                self.state["completed"].append(passed_id)
            self.state["cursor"] = min(self.state["cursor"] + 1, len(self.levels))
            self.save()
            nxt = self.current_level()
            self.note(f"第 {lv['order']} 关通过，容器已销毁", "pass")
            return {
                "pass": True,
                "output": output[-8000:] if output else raw.strip()[-8000:],
                "checks": checks,
                "level_id": passed_id,
                "solution": lv["solution"],
                "next": None if nxt is None else {
                    "id": nxt["id"], "title": nxt["title"], "order": nxt["order"]
                },
                "finished": nxt is None,
            }

    def skip(self):
        """跳过当前关（只有标了 skippable 的关卡允许）。跳过的关不计分。"""
        with LOCK:
            lv = self.current_level()
            if lv is None:
                raise DockerError("没有可跳过的关卡，课程已经走完")
            if not lv.get("skippable"):
                raise DockerError(f"第 {lv['order']} 关不能跳过（只有标注了可跳过的关卡才允许）")

            self.stop_session(reason=f"跳过 {lv['id']}")
            skipped_id = lv["id"]
            if skipped_id not in self.state["skipped"]:
                self.state["skipped"].append(skipped_id)
            self.state["completed"] = [x for x in self.state["completed"] if x != skipped_id]
            self.state["cursor"] = min(self.state["cursor"] + 1, len(self.levels))
            self.save()
            self.note(f"已跳过第 {lv['order']} 关（{lv['id']}），不计分", "info")
            nxt = self.current_level()
            return {
                "skipped_level": skipped_id,
                "next": None if nxt is None else {"id": nxt["id"], "title": nxt["title"], "order": nxt["order"]},
                "finished": nxt is None,
            }

    def jump_to(self, index):
        """跳到指定关卡（教学演示用：老师不必先通关前 9 关）。"""
        with LOCK:
            if not (0 <= index < len(self.levels)):
                raise DockerError(f"关卡序号越界：{index}，共 {len(self.levels)} 关")
            self.stop_session(reason="跳关")
            self.state["cursor"] = index
            self.save()
            lv = self.levels[index]
            self.note(f"跳转到第 {lv['order']} 关 {lv['id']}", "info")
            return self.snapshot()

    def reset_progress(self):
        with LOCK:
            self.stop_session(reason="reset")
            self.state["cursor"] = 0
            self.state["completed"] = []
            self.state["skipped"] = []
            self.state["log"] = []
            self.save()
            self.note("进度已重置", "info")

    def snapshot(self):
        s = self.session_info()
        cur = self.current_level()
        return {
            "levels": self.public_levels(),
            "cursor": self.state["cursor"],
            "completed": self.state["completed"],
            "skipped": self.state["skipped"],
            "current": None if cur is None else {
                "id": cur["id"], "order": cur["order"], "title": cur["title"],
                "summary": cur["summary"], "objectives": cur["objectives"],
                "hints": cur["hints"], "workdir": cur["workdir"],
                "points": cur.get("points", 100),
                "category": cur["category"], "category_label": cur["category_label"],
                "tool": cur["tool"], "tool_label": cur["tool_label"],
                "vscode": bool(cur.get("vscode")),
                "skippable": bool(cur.get("skippable")),
                "skip_reason": cur.get("skip_reason", ""),
                "platform_notes": cur["platform_notes"],
                "method": cur.get("method", {}),
                "symptom": cur["symptom"], "diagnose": cur["diagnose"],
                "solution": cur["solution"],
            },
            "session": s,
            "log": self.state["log"][-40:],
            "finished": cur is None,
        }
