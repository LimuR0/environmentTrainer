"""宿主机环境体检：检查这台机器上跑这门课需要的工具，并按当前系统给出安装命令。

这是「教会三个系统怎么弄环境」的落点 —— 容器里是 Linux，但学员的电脑是 macOS / Windows / Linux，
每个东西的安装方式、配置文件、PATH 写法都不一样。
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys

from platform_util import (
    IS_MAC,
    IS_WIN,
    NO_WINDOW,
    TEXT_KW,
    find_docker,
    platform_name,
)

# 每一项：id / 名称 / 是否必需 / 三平台安装命令 / 说明
CATALOG = [
    {
        "id": "python",
        "name": "Python 3.9+",
        "required": True,
        "why": "后端服务本体（零第三方依赖，只用标准库）",
        "install": {
            "macos": ["brew install python@3.12", "或到 python.org 下载 macOS 安装包"],
            "windows": [
                "winget install -e --id Python.Python.3.12",
                "安装向导里务必勾选 Add python.exe to PATH",
            ],
            "linux": [
                "sudo apt install python3 python3-venv   # Debian/Ubuntu",
                "sudo dnf install python3                 # Fedora",
                "sudo pacman -S python                    # Arch",
            ],
        },
    },
    {
        "id": "docker",
        "name": "Docker（守护进程在跑）",
        "required": True,
        "why": "每一关都是一个容器",
        "install": {
            "macos": [
                "brew install --cask orbstack        # 或 docker",
                "brew install --cask docker",
                "装完打开 OrbStack / Docker Desktop，等图标变绿",
            ],
            "windows": [
                "winget install -e --id Docker.DockerDesktop",
                "设置里确认勾选 Use the WSL 2 based engine",
                "首次启动需要启用 WSL2：wsl --install",
            ],
            "linux": [
                "curl -fsSL https://get.docker.com | sudo sh",
                "sudo systemctl enable --now docker",
                "sudo usermod -aG docker $USER   # 然后重新登录，才能免 sudo",
            ],
        },
    },
    {
        "id": "git",
        "name": "Git",
        "required": False,
        "why": "克隆课程仓库 / 后续实战项目都需要",
        "install": {
            "macos": ["brew install git", "（xcode-select --install 也会带上 git）"],
            "windows": ["winget install -e --id Git.Git"],
            "linux": ["sudo apt install git   # Debian/Ubuntu", "sudo dnf install git   # Fedora"],
        },
    },
    {
        "id": "node",
        "name": "Node.js 20+（可选）",
        "required": False,
        "why": "课程第 7、8 关在容器里跑，宿主机不装也能学；本地做前端实验才需要",
        "install": {
            "macos": ["brew install node@20", "或 brew install fnm && fnm install 20"],
            "windows": [
                "winget install -e --id OpenJS.NodeJS.LTS",
                "推荐用 fnm：winget install Schniz.fnm",
            ],
            "linux": [
                "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -",
                "sudo apt install -y nodejs",
            ],
        },
    },
]

PKG_MANAGERS = {
    "macos": [("brew", "Homebrew"), ("port", "MacPorts")],
    "windows": [("winget", "winget"), ("choco", "Chocolatey"), ("scoop", "Scoop")],
    "linux": [("apt-get", "apt"), ("dnf", "dnf"), ("pacman", "pacman"), ("zypper", "zypper"), ("apk", "apk")],
}


def _run(argv, timeout=12):
    try:
        cp = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            creationflags=NO_WINDOW,
            **TEXT_KW,
        )
        return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()
    except Exception:
        return 1, "", ""


def _first_line(text):
    return text.splitlines()[0].strip() if text else ""


def _which(name):
    return shutil.which(name)


def _python_info():
    ver = ".".join(str(x) for x in sys.version_info[:3])
    ok = sys.version_info >= (3, 9)
    return {
        "ok": ok,
        "version": ver,
        "path": sys.executable,
        "detail": f"{ver}（{sys.executable}）" if ok else f"{ver} 太旧，需要 3.9+",
    }


def _docker_info():
    exe = find_docker()
    if not exe:
        return {"ok": False, "version": "", "path": "", "detail": "找不到 docker 命令"}
    rc, out, err = _run([exe, "version", "--format", "{{.Client.Version}}"])
    client = _first_line(out) if rc == 0 else ""
    rc2, out2, err2 = _run([exe, "info", "--format", "{{.ServerVersion}}"], timeout=20)
    if rc2 != 0:
        tail = _first_line(err2 or out2)
        return {
            "ok": False,
            "version": client,
            "path": exe,
            "detail": f"CLI 在，但守护进程没响应：{tail}" if tail else "CLI 在，但守护进程没响应",
        }
    return {"ok": True, "version": f"client {client} / server {_first_line(out2)}", "path": exe, "detail": "守护进程可用"}


def _tool_info(cmd, args=("--version",)):
    exe = _which(cmd)
    if not exe:
        return {"ok": False, "version": "", "path": "", "detail": "未安装"}
    rc, out, err = _run([exe, *args])
    text = _first_line(out or err)
    return {"ok": rc == 0, "version": text, "path": exe, "detail": text or "已安装"}


def _shell_info():
    if IS_WIN:
        shell = os.environ.get("PSModulePath") and "powershell" or "cmd"
        profile = os.path.expandvars(r"%USERPROFILE%\Documents\PowerShell\Microsoft.PowerShell_profile.ps1")
        return {
            "name": "PowerShell" if shell == "powershell" else "cmd",
            "config": profile if shell == "powershell" else "系统属性 → 环境变量（GUI）",
            "note": "Windows 上 PATH 改完要重开终端；临时改：$env:Path = \"C:\\新路径;\" + $env:Path",
        }
    sh = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
    if sh == "zsh":
        cfg = "~/.zshrc"
    elif sh == "fish":
        cfg = "~/.config/fish/config.fish"
    elif IS_MAC:
        cfg = "~/.bash_profile"
    else:
        cfg = "~/.bashrc"
    return {
        "name": sh,
        "config": cfg,
        "note": f"改完执行 source {cfg} 生效；新开终端也会自动读",
    }


def _pkg_manager():
    found = []
    for cmd, label in PKG_MANAGERS.get(platform_name(), []):
        exe = _which(cmd)
        if exe:
            found.append({"cmd": cmd, "label": label, "path": exe})
    return found


def _os_label():
    if IS_MAC:
        v = platform.mac_ver()[0] or platform.release()
        return f"macOS {v}"
    if IS_WIN:
        return f"{platform.system()} {platform.release()} ({platform.version()})"
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            lines = dict(
                line.strip().split("=", 1) for line in f if "=" in line
            )
        name = lines.get("PRETTY_NAME", "").strip('"')
        return name or f"Linux {platform.release()}"
    except Exception:
        return f"Linux {platform.release()}"


def _probe(item_id):
    if item_id == "python":
        return _python_info()
    if item_id == "docker":
        return _docker_info()
    if item_id == "git":
        return _tool_info("git")
    if item_id == "node":
        return _tool_info("node", ("-v",))
    return {"ok": False, "version": "", "path": "", "detail": "未知项"}


def host_report():
    plat = platform_name()
    checks = []
    for item in CATALOG:
        info = _probe(item["id"])
        checks.append(
            {
                "id": item["id"],
                "name": item["name"],
                "required": item["required"],
                "why": item["why"],
                "ok": info["ok"],
                "version": info["version"],
                "path": info["path"],
                "detail": info["detail"],
                "install": item["install"],
            }
        )

    missing_required = [c for c in checks if c["required"] and not c["ok"]]
    return {
        "platform": plat,
        "platform_label": _os_label(),
        "arch": platform.machine(),
        "shell": _shell_info(),
        "package_managers": _pkg_manager(),
        "checks": checks,
        "ready": len(missing_required) == 0,
        "missing_required": [c["id"] for c in missing_required],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(host_report(), ensure_ascii=False, indent=2))
