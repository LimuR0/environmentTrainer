"""跨平台小工具：平台判定、进程管道编码、可执行文件查找。

这里集中处理 macOS / Linux / Windows 的差异，别的模块只调用这里的函数。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# Windows 上 subprocess 默认用 locale 编码（中文系统是 cp936），
# 而 docker 的输出是 UTF-8，不显式指定会 UnicodeDecodeError。
TEXT_KW = dict(text=True, encoding="utf-8", errors="replace")

# 让子进程不弹黑窗（Windows 专用 flag，别的平台为 0）
NO_WINDOW = 0x08000000 if IS_WIN else 0


def platform_name() -> str:
    if IS_WIN:
        return "windows"
    if IS_MAC:
        return "macos"
    if IS_LINUX:
        return "linux"
    return sys.platform


def find_docker() -> str | None:
    """找 docker 可执行文件，顺带照顾 Windows 上 Docker Desktop 的默认安装位置。"""
    p = shutil.which("docker")
    if p:
        return p
    if IS_WIN:
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Docker\Docker\resources\bin\docker.exe"),
            os.path.expandvars(r"%ProgramData%\DockerDesktop\version-bin\docker.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Docker\wsl\docker.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
    else:
        for c in ("/usr/local/bin/docker", "/opt/homebrew/bin/docker", "/usr/bin/docker"):
            if os.path.isfile(c):
                return c
    return None


def find_python() -> str:
    return sys.executable or ("python" if IS_WIN else "python3")


def run_capture(argv, timeout=30, cwd=None):
    """同步执行并捕获输出（强制 UTF-8）。"""
    return subprocess.run(
        argv,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
        creationflags=NO_WINDOW,
        **TEXT_KW,
    )


def popen(argv, **kwargs):
    """统一的 Popen 封装：Windows 上不弹窗、管道用 UTF-8。"""
    kwargs.setdefault("creationflags", NO_WINDOW)
    if kwargs.pop("text_mode", False):
        kwargs.update(TEXT_KW)
    return subprocess.Popen(argv, **kwargs)


def kill_tree(proc, timeout=3.0):
    """尽力把一个子进程连同它的进程树干净地结束。"""
    if proc is None:
        return
    try:
        if IS_WIN:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                creationflags=NO_WINDOW,
            )
        else:
            try:
                os.killpg(os.getpgid(proc.pid), 15)  # SIGTERM
            except Exception:
                proc.terminate()
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=timeout)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def capabilities() -> dict:
    """给 start.py --check 用的能力报告。"""
    caps = {
        "platform": platform_name(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "docker": find_docker(),
        "pty": False,
        "conpty": False,
    }
    try:
        import pty  # noqa: F401

        caps["pty"] = True
    except Exception:
        pass
    if IS_WIN:
        try:
            import ctypes

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            caps["conpty"] = hasattr(k32, "CreatePseudoConsole")
        except Exception:
            caps["conpty"] = False
    return caps
