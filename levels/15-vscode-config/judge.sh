#!/usr/bin/env bash
# 第 15 关判题：检查 .vscode/ 四个配置文件（允许 JSONC 注释/尾逗号），并真的执行 tasks 里的命令
cd /work/pyapp 2>/dev/null || { echo "CHECK|fail|工作目录|/work/pyapp 不存在"; echo "RESULT|fail"; exit 1; }

python3 - <<'PYEOF'
import json, os, re, subprocess, sys

def strip_jsonc(text):
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if c == '"':
                in_str = False
            i += 1; continue
        if c == '"':
            in_str = True; out.append(c); i += 1; continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2; continue
        out.append(c); i += 1
    s = "".join(out).lstrip("\ufeff")
    return re.sub(r",(\s*[}\]])", r"\1", s)

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.loads(strip_jsonc(f.read()))

def ok(name, detail=""):
    print("CHECK|ok|%s|%s" % (name, detail))

def bad(name, detail=""):
    print("CHECK|fail|%s|%s" % (name, detail))

res = {}
VS = "/work/pyapp/.vscode"

# settings.json
sp = os.path.join(VS, "settings.json")
settings = None
if not os.path.isfile(sp):
    bad("settings.json", "文件不存在")
else:
    try:
        settings = load(sp)
    except Exception as e:
        bad("settings.json", "JSON 解析失败：%s" % e)
if settings is not None:
    interp = str(settings.get("python.defaultInterpreterPath", ""))
    cand = interp.replace("${workspaceFolder}", "/work/pyapp")
    if cand and not os.path.isabs(cand):
        cand = os.path.join("/work/pyapp", cand)
    interp_ok = bool(cand) and os.path.isfile(cand)
    if interp_ok:
        ok("settings.json · 解释器", interp)
    else:
        bad("settings.json · 解释器", "python.defaultInterpreterPath=%r 指向不存在的文件" % interp)
    pytest_on = settings.get("python.testing.pytestEnabled") is True
    if pytest_on:
        ok("settings.json · 测试发现", "pytest 已启用")
    else:
        bad("settings.json · 测试发现", "缺 python.testing.pytestEnabled = true")
    res["settings"] = interp_ok and pytest_on

# launch.json
lp = os.path.join(VS, "launch.json")
launch = None
if not os.path.isfile(lp):
    bad("launch.json", "文件不存在")
else:
    try:
        launch = load(lp)
    except Exception as e:
        bad("launch.json", "JSON 解析失败：%s" % e)
hit = None
if launch:
    for c in launch.get("configurations") or []:
        prog = str(c.get("program", ""))
        if "app.py" in prog and str(c.get("type", "")).lower() in ("python", "debugpy"):
            hit = c
            break
if hit:
    ok("launch.json · 调试配置", "%s → %s" % (hit.get("name") or "unnamed", hit.get("program")))
else:
    if launch is not None:
        bad("launch.json · 调试配置", "没有 type=python/debugpy 且 program 指向 app.py 的配置")
res["launch"] = bool(hit)

# tasks.json
tp = os.path.join(VS, "tasks.json")
tasks = None
if not os.path.isfile(tp):
    bad("tasks.json", "文件不存在")
else:
    try:
        tasks = load(tp)
    except Exception as e:
        bad("tasks.json", "JSON 解析失败：%s" % e)
test_task = None
if tasks:
    for t in tasks.get("tasks") or []:
        cmd = str(t.get("command", ""))
        args = " ".join(str(a) for a in (t.get("args") or []))
        label = str(t.get("label", "")).lower()
        if "pytest" in (cmd + " " + args) or label in ("test", "tests", "pytest"):
            test_task = t
            break
if test_task:
    ok("tasks.json · 测试任务", "%s: %s %s" % (test_task.get("label"), test_task.get("command"), " ".join(map(str, test_task.get("args") or []))))
else:
    if tasks is not None:
        bad("tasks.json · 测试任务", "没有找到跑 pytest 的 task")
res["tasks"] = bool(test_task)

# extensions.json
ep = os.path.join(VS, "extensions.json")
ext = None
if not os.path.isfile(ep):
    bad("extensions.json", "文件不存在")
else:
    try:
        ext = load(ep)
    except Exception as e:
        bad("extensions.json", "JSON 解析失败：%s" % e)
hit_ext = []
if ext:
    recs = [str(x) for x in (ext.get("recommendations") or [])]
    hit_ext = [r for r in recs if "python" in r.lower()]
if hit_ext:
    ok("extensions.json · 推荐扩展", ", ".join(hit_ext[:3]))
else:
    if ext is not None:
        bad("extensions.json · 推荐扩展", "recommendations 里没有 Python 相关扩展")
res["extensions"] = bool(hit_ext)

# 真的执行 tasks.json 里的命令
if test_task:
    cmd = str(test_task.get("command", ""))
    args = [str(a) for a in (test_task.get("args") or [])]
    opts = test_task.get("options") or {}
    cwd = str(opts.get("cwd") or "/work/pyapp").replace("${workspaceFolder}", "/work/pyapp")
    if cmd and "/" in cmd:
        cmd = cmd.replace("${workspaceFolder}", "/work/pyapp")
        if not os.path.isabs(cmd):
            cmd = os.path.join(cwd, cmd)
    try:
        proc = subprocess.run([cmd] + args, cwd=cwd, capture_output=True, text=True, timeout=120)
        outp = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0 and "passed" in outp:
            ok("任务可执行", outp.strip().splitlines()[-1])
            res["run"] = True
        else:
            bad("任务可执行", (outp.strip().splitlines() or ["退出码 %d" % proc.returncode])[-1])
            res["run"] = False
    except Exception as e:
        bad("任务可执行", str(e))
        res["run"] = False
else:
    res["run"] = False

passed = all(res.get(k, False) for k in ("settings", "launch", "tasks", "extensions", "run"))
print("RESULT|" + ("pass" if passed else "fail"))
sys.exit(0 if passed else 1)
PYEOF
