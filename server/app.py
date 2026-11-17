"""Environment Trainer 后端：HTTP API + WebSocket 终端。

零第三方依赖，只用 Python 标准库；容器编排走 docker CLI。
三个平台都支持：

  macOS / Linux : server/term.py 的 PosixPTY（完整 TTY）
  Windows 10 1809+ / 11 : WinConPTY（ConPTY），失败自动降级为管道模式

启动： python start.py            （推荐，会做环境自检）
       python server/app.py --port 8181
"""

import argparse
import codecs
import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# 允许 `python server/app.py` 直接跑（把 server/ 放进 sys.path）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hostcheck  # noqa: E402
import term  # noqa: E402
from docker_ctl import DockerError, docker_bin, reap_networks, reap_orphans  # noqa: E402
from levels import LevelStore, ROOT  # noqa: E402
from platform_util import IS_WIN, capabilities, platform_name  # noqa: E402
from ws import WSClosed, WSConn, accept_key  # noqa: E402

WEB_DIR = os.path.join(ROOT, "web")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".map": "application/json",
}

STORE = None  # type: LevelStore


class TrainerHTTPServer(ThreadingHTTPServer):
    # Windows 的 SO_REUSEADDR 允许抢占已占用端口，这里关掉，端口冲突就明确报错
    allow_reuse_address = not IS_WIN
    daemon_threads = True


def log(msg):
    print(f"[server] {msg}", flush=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "EnvTrainer/1.0"

    # ---------------- 基础 ----------------
    def log_message(self, fmt, *args):
        if os.environ.get("ENVTRAINER_VERBOSE"):
            log(fmt % args)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _err(self, msg, code=400):
        self._json({"ok": False, "error": str(msg)}, code=code)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _static(self, rel):
        rel = rel.lstrip("/").replace("\\", "/")
        path = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not (path == WEB_DIR or path.startswith(WEB_DIR + os.sep)):
            return self._err("bad path", 403)
        if not os.path.isfile(path):
            return self._err("not found", 404)
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    # ---------------- GET ----------------
    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            if u.path == "/api/host":
                return self._json({"ok": True, **hostcheck.host_report()})
            if u.path == "/api/state":
                return self._json({"ok": True, **STORE.snapshot()})
            if u.path == "/api/health":
                caps = capabilities()
                try:
                    docker_bin()
                    docker_ok = True
                    detail = None
                except DockerError as e:
                    docker_ok = False
                    detail = str(e)
                return self._json(
                    {
                        "ok": True,
                        "docker": docker_ok,
                        "detail": detail,
                        "platform": caps["platform"],
                        "python": caps["python"],
                        "terminal": "conpty" if caps["conpty"] else ("pty" if caps["pty"] else "pipe"),
                    }
                )
            return self._err("unknown api", 404)

        if (self.headers.get("Upgrade") or "").lower() == "websocket":
            return self._ws_terminal(u)

        if u.path in ("/", "/index.html"):
            return self._static("index.html")
        return self._static(u.path)

    # ---------------- POST ----------------
    def do_POST(self):
        u = urlparse(self.path)
        try:
            if u.path == "/api/session/start":
                info = STORE.start_session()
                return self._json({"ok": True, "session": info, **STORE.snapshot()})
            if u.path == "/api/session/stop":
                STORE.stop_session(reason="用户手动关闭")
                return self._json({"ok": True, **STORE.snapshot()})
            if u.path == "/api/check":
                res = STORE.judge()
                return self._json({"ok": True, "result": res, **STORE.snapshot()})
            if u.path == "/api/skip":
                return self._json({"ok": True, **STORE.skip(), **STORE.snapshot()})
            if u.path == "/api/jump":
                body = self._body()
                return self._json({"ok": True, **STORE.jump_to(int(body.get("index", 0)))})
            if u.path == "/api/reset":
                STORE.reset_progress()
                return self._json({"ok": True, **STORE.snapshot()})
            return self._err("unknown api", 404)
        except DockerError as e:
            return self._err(e, 500)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._err(f"{type(e).__name__}: {e}", 500)

    # ---------------- WebSocket 终端 ----------------
    def _ws_terminal(self, u):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            return self._err("缺少 Sec-WebSocket-Key", 400)

        qs = parse_qs(u.query)
        try:
            cols = max(20, min(300, int(qs.get("cols", ["100"])[0])))
            rows = max(6, min(120, int(qs.get("rows", ["30"])[0])))
        except ValueError:
            cols, rows = 100, 30

        sess = STORE.session_info()
        cid = (sess or {}).get("container")
        level = STORE.current_level()

        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept_key(key))
        self.end_headers()
        self.close_connection = True

        ws = WSConn(self.rfile, self.wfile)
        if not cid:
            ws.send_text(
                json.dumps(
                    {"t": "o", "d": "\r\n\x1b[31m[!] 没有运行中的容器，请先点『开始 / 重开本关』\x1b[0m\r\n"}
                )
            )
            ws.close()
            return

        workdir = (level or {}).get("workdir", "/work")
        self._pump_terminal(ws, cid, workdir, cols, rows)

    def _pump_terminal(self, ws, cid, workdir, cols, rows):
        try:
            sess = term.create_terminal(docker_bin(), cid, workdir, cols, rows)
        except Exception as e:  # noqa: BLE001
            try:
                ws.send_text(
                    json.dumps({"t": "o", "d": f"\r\n\x1b[31m[!] 无法进入容器：{e}\x1b[0m\r\n"})
                )
                ws.close()
            except WSClosed:
                pass
            return

        try:
            ws.send_text(
                json.dumps({"t": "hello", "mode": sess.mode, "label": term.mode_label(sess.mode)})
            )
        except WSClosed:
            sess.terminate()
            return

        stop = threading.Event()
        dec = codecs.getincrementaldecoder("utf-8")("replace")

        def reader():
            while not stop.is_set():
                try:
                    data = sess.read(65536)
                except Exception:  # noqa: BLE001
                    break
                if not data:
                    break
                try:
                    ws.send_text(json.dumps({"t": "o", "d": dec.decode(data)}))
                except WSClosed:
                    break
            stop.set()
            try:
                ws.send_text(json.dumps({"t": "exit"}))
            except WSClosed:
                pass

        th = threading.Thread(target=reader, daemon=True)
        th.start()

        try:
            while not stop.is_set():
                try:
                    opcode, data = ws.recv()
                except WSClosed:
                    break
                if opcode != 0x1:
                    continue
                try:
                    msg = json.loads(data.decode("utf-8", "replace"))
                except Exception:
                    continue
                t = msg.get("t")
                if t == "i":
                    payload = msg.get("d") or ""
                    if payload:
                        if sess.mode == term.PIPE:
                            echo = []
                            for ch in payload:
                                if ch == "\r":
                                    echo.append("\r\n")
                                elif ch in ("\x7f", "\b"):
                                    echo.append("\b \b")
                                elif ch >= " ":
                                    echo.append(ch)
                            if echo:
                                try:
                                    ws.send_text(json.dumps({"t": "o", "d": "".join(echo)}))
                                except WSClosed:
                                    break
                        sess.write(payload.encode("utf-8"))
                elif t == "r":
                    try:
                        c = max(20, min(300, int(msg.get("cols", cols))))
                        r = max(6, min(120, int(msg.get("rows", rows))))
                        sess.resize(c, r)
                    except Exception:
                        pass
                elif t == "p":
                    try:
                        ws.ping()
                    except WSClosed:
                        break
        finally:
            stop.set()
            sess.terminate()
            try:
                STORE.session_info()  # 顺手清理已销毁容器留下的会话状态
            except Exception:
                pass


def main(argv=None):
    global STORE

    ap = argparse.ArgumentParser(description="Environment Trainer server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8181)
    ap.add_argument("--keep-orphans", action="store_true", help="启动时不清理残留容器")
    args = ap.parse_args(argv)

    log(f"平台: {platform_name()}  python {sys.version.split()[0]}")
    caps = capabilities()
    log(
        "终端能力: "
        + ", ".join(
            [
                f"conpty={'yes' if caps['conpty'] else 'no'}",
                f"pty={'yes' if caps['pty'] else 'no'}",
                "降级管道=可用",
            ]
        )
    )

    if not args.keep_orphans:
        try:
            reap_orphans(log=log)
            reap_networks(log=log)
        except DockerError as e:
            log(f"清理残留容器失败（可以忽略）: {e}")

    STORE = LevelStore()
    log(f"已加载 {len(STORE.levels)} 个关卡: {[l['id'] for l in STORE.levels]}")

    httpd = TrainerHTTPServer((args.host, args.port), Handler)
    log(f"前端 -> http://{args.host}:{args.port}")

    def shutdown(*_):
        log("正在退出，清理容器…")
        try:
            STORE.stop_session(reason="服务关闭")
        except Exception:
            pass
        os._exit(0)

    try:
        import signal

        signal.signal(signal.SIGINT, shutdown)
        if not IS_WIN:
            signal.signal(signal.SIGTERM, shutdown)
    except Exception:
        pass

    try:
        httpd.serve_forever(poll_interval=0.4)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
