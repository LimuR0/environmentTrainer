#!/usr/bin/env python3
"""Environment Trainer 启动器（macOS / Windows / Linux 通用）。

    python start.py                 启动（默认 http://127.0.0.1:8181）
    python start.py --check         只做环境自检，不启动
    python start.py --port 9000     指定端口
    python start.py --no-browser    不自动打开浏览器

三个平台都用同一个入口，run.sh / run.bat / run.ps1 只是薄封装。
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(ROOT, "server")
sys.path.insert(0, SERVER_DIR)

MIN_PY = (3, 9)


def _c(text, code):
    """终端颜色；Windows 老控制台不支持 ANSI 时自动跳过。"""
    if os.environ.get("NO_COLOR") or (os.name == "nt" and not os.environ.get("WT_SESSION")):
        return text
    return f"\033[{code}m{text}\033[0m"


def ok(msg):
    print(f"  {_c('✓', '32')} {msg}")


def bad(msg):
    print(f"  {_c('✗', '31')} {msg}")


def warn(msg):
    print(f"  {_c('!', '33')} {msg}")


def port_available(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def pick_port(host, wanted, tries=20):
    for p in range(wanted, wanted + tries):
        if port_available(host, p):
            return p
    return None


def check_python():
    if sys.version_info < MIN_PY:
        bad(
            "Python 版本太旧：%s，需要 %s+"
            % (sys.version.split()[0], ".".join(map(str, MIN_PY)))
        )
        print("     macOS  : brew install python@3.12")
        print("     Windows: https://www.python.org/downloads/  （安装时勾选 Add to PATH）")
        print("     Linux  : sudo apt install python3")
        return False
    ok("Python %s（%s）" % (sys.version.split()[0], sys.executable))
    return True


def check_docker():
    from docker_ctl import DockerError, docker_bin

    try:
        exe = docker_bin()
    except DockerError as e:
        bad(str(e))
        return False
    ok(f"docker: {exe}")

    import subprocess

    from platform_util import NO_WINDOW, TEXT_KW

    try:
        cp = subprocess.run(
            [exe, "info", "--format", "{{.ServerVersion}} {{.OperatingSystem}}"],
            capture_output=True,
            timeout=20,
            creationflags=NO_WINDOW,
            **TEXT_KW,
        )
    except Exception as e:  # noqa: BLE001
        bad(f"docker info 执行失败：{e}")
        return False
    if cp.returncode != 0:
        bad("docker 守护进程没在跑（或当前用户没有权限）")
        tail = (cp.stderr or "").strip().splitlines()[:3]
        for line in tail:
            print(f"     {line}")
        print("     macOS  : 打开 OrbStack / Docker Desktop")
        print("     Windows: 打开 Docker Desktop，确认 WSL2 后端已启用")
        print("     Linux  : sudo systemctl start docker  并把自己加进 docker 组")
        return False
    ok(f"docker 守护进程可用：{cp.stdout.strip()}")
    return True


def check_terminal():
    from platform_util import IS_WIN, capabilities

    caps = capabilities()
    if caps["pty"]:
        ok("终端后端：PosixPTY（完整 TTY，支持 vim / top 等交互程序）")
        return "pty"
    if caps["conpty"]:
        ok("终端后端：Windows ConPTY（完整 TTY）")
        return "conpty"
    warn("终端后端：兼容模式（无 TTY）—— 命令能跑，交互式程序不可用")
    if IS_WIN:
        print("     ConPTY 需要 Windows 10 1809+ / Windows 11")
    return "pipe"


def check_mirrors(refresh=False):
    from mirrors import load_or_pick, summary

    if refresh:
        print("  正在探测镜像站延迟…")
        mirrors = load_or_pick(force=True, log=None)
    else:
        mirrors = load_or_pick(force=False, log=None)
    ok(summary(mirrors))
    return mirrors


def check_levels():
    from levels import LevelStore

    store = LevelStore()
    if not store.levels:
        bad("levels/ 目录下没有关卡（缺 level.json）")
        return None
    ok(f"关卡：{len(store.levels)} 个 -> {', '.join(l['id'] for l in store.levels)}")
    return store


def check_images():
    """提示哪些镜像还没构建（第一次开始某关时会自动构建）。"""
    import subprocess

    from docker_ctl import DockerError, docker_bin, image_exists
    from platform_util import NO_WINDOW, TEXT_KW

    try:
        exe = docker_bin()
    except DockerError:
        return
    missing = []
    from levels import LevelStore

    for lv in LevelStore().levels:
        try:
            if not image_exists(lv["image"]):
                missing.append(lv["image"])
        except Exception:
            pass
    if not missing:
        ok("关卡镜像：全部已构建")
    else:
        warn(f"{len(missing)} 个镜像还没构建（第一次点『开始』时会自动 build，会慢一点）")
        for m in missing[:5]:
            print(f"     {m}")


def do_check(host="127.0.0.1", port=8181):
    print(_c("Environment Trainer 环境自检", "1"))
    print()
    good = check_python()
    if not good:
        return 1
    docker_ok = check_docker()
    check_mirrors()
    check_terminal()
    store = check_levels()
    if docker_ok and store:
        check_images()
    print()
    free = port_available(host, port)
    if free:
        ok(f"端口 {port} 可用")
    else:
        nxt = pick_port(host, port + 1)
        warn(f"端口 {port} 被占用" + (f"，启动时会用 {nxt}" if nxt else "，也找不到别的空闲端口"))
    print()
    if good and docker_ok and store:
        print(_c("可以启动了：python start.py", "32"))
        return 0
    print(_c("还有问题没解决，先按上面的提示处理", "31"))
    return 1


def main():
    ap = argparse.ArgumentParser(description="Environment Trainer")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8181)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--check", action="store_true", help="只做环境自检")
    ap.add_argument("--mirrors", action="store_true", help="重新探测最快的包镜像源")
    ap.add_argument("--keep-orphans", action="store_true")
    args = ap.parse_args()

    if args.mirrors:
        from mirrors import load_or_pick, summary

        print("正在探测镜像站…")
        mirrors = load_or_pick(force=True, log=print)
        print()
        print(summary(mirrors))
        print("已写入 .mirrors.json，下次构建镜像自动生效。")
        return 0

    if args.check:
        return do_check(args.host, args.port)

    if not check_python():
        return 1
    if not check_docker():
        return 1

    port = args.port
    if not port_available(args.host, port):
        found = pick_port(args.host, port + 1)
        if not found:
            bad(f"端口 {port} 被占用，附近也找不到空闲端口，用 --port 指定一个")
            return 1
        warn(f"端口 {port} 被占用，改用 {found}")
        port = found

    url = f"http://{args.host}:{port}"
    if not args.no_browser:
        def open_later():
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass

        threading.Thread(target=open_later, daemon=True).start()

    import app as server_app

    argv = ["--host", args.host, "--port", str(port)]
    if args.keep_orphans:
        argv.append("--keep-orphans")
    server_app.main(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
