"""docker CLI 封装：构建镜像、起容器、跑判题脚本、销毁。

刻意只调用 docker CLI（不做 SDK 依赖），方便在任何装了 docker 的机器上跑。
"""

import subprocess
import threading

from mirrors import build_args as mirror_build_args
from platform_util import NO_WINDOW, TEXT_KW, find_docker, run_capture

BUILD_LOCK = threading.Lock()
_DOCKER_BIN = None


class DockerError(RuntimeError):
    pass


def docker_bin() -> str:
    """docker 可执行文件路径（带缓存）。macOS / Linux / Windows 都走 platform_util。"""
    global _DOCKER_BIN
    if _DOCKER_BIN:
        return _DOCKER_BIN
    p = find_docker()
    if not p:
        raise DockerError(
            "找不到 docker 命令。请先安装并启动 Docker：\n"
            "  macOS   : OrbStack 或 Docker Desktop\n"
            "  Windows : Docker Desktop（需要 WSL2 后端）\n"
            "  Linux   : apt/dnf 安装 docker-ce，并把当前用户加入 docker 组"
        )
    _DOCKER_BIN = p
    return p


def _run(args, timeout=120, check=True, env=None) -> subprocess.CompletedProcess:
    cmd = [docker_bin()] + args
    try:
        cp = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            env=env,
            creationflags=NO_WINDOW,
            **TEXT_KW,
        )
    except subprocess.TimeoutExpired as e:
        raise DockerError(f"docker 命令超时: {' '.join(cmd)}") from e
    if check and cp.returncode != 0:
        raise DockerError(f"{' '.join(cmd)}\n{cp.stderr.strip()[-2000:]}")
    return cp


def image_exists(tag: str) -> bool:
    cp = _run(["image", "inspect", tag], timeout=30, check=False)
    return cp.returncode == 0


def build_image(tag: str, context_dir: str, log=print) -> None:
    """按目录构建镜像；用文件锁串行化，避免并发构建打架。"""
    with BUILD_LOCK:
        log(f"[docker] 构建镜像 {tag} <- {context_dir}")
        cmd = [docker_bin(), "build", "-t", tag]
        for k, v in mirror_build_args().items():
            cmd += ["--build-arg", f"{k}={v}"]
        cmd.append(context_dir)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=NO_WINDOW,
            **TEXT_KW,
        )
        tail = []
        for line in proc.stdout:
            line = line.rstrip()
            tail.append(line)
            if len(tail) > 60:
                tail.pop(0)
        code = proc.wait()
        if code != 0:
            raise DockerError("镜像构建失败:\n" + "\n".join(tail[-40:]))
        log(f"[docker] 镜像 {tag} 就绪")


def ensure_image(tag: str, context_dir: str, log=print) -> None:
    if image_exists(tag):
        return
    build_image(tag, context_dir, log=log)


def run_container(name: str, image: str, labels: dict, workdir: str = "/work", publish=None,
                  network=None, alias=None, command=None) -> str:
    """后台起一个常驻容器，返回容器 id。"""
    remove_container(name)
    args = [
        "run", "-d",
        "--name", name,
        "--hostname", "sandbox",
        "--label", "envtrainer=1",
    ]
    for k, v in labels.items():
        args += ["--label", f"{k}={v}"]
    if publish:
        args += ["-p", publish]
    if network:
        args += ["--network", network]
        if alias:
            args += ["--network-alias", alias]
    args += [
        "--memory", "1g",
        "--memory-swap", "1g",
        "--pids-limit", "512",
        "--cpus", "1.5",
        "-w", workdir,
        image,
    ] + (list(command) if command else ["sleep", "infinity"])
    cp = _run(args, timeout=120)
    cid = cp.stdout.strip()
    if not cid:
        raise DockerError("docker run 没有返回容器 id")
    return cid


def create_network(name: str, internal: bool = False) -> None:
    _run(["network", "rm", "-f", name], timeout=30, check=False)
    args = ["network", "create", "--label", "envtrainer=1"]
    if internal:
        args.append("--internal")
    args.append(name)
    _run(args, timeout=30)


def remove_network(name: str) -> None:
    if not name:
        return
    _run(["network", "rm", "-f", name], timeout=30, check=False)


def connect_network(network: str, cid: str) -> None:
    _run(["network", "connect", network, cid], timeout=30, check=False)


def reap_networks(log=print) -> int:
    cp = _run(["network", "ls", "-q", "--filter", "label=envtrainer=1"], timeout=30, check=False)
    nets = [x for x in cp.stdout.split() if x]
    for n in nets:
        remove_network(n)
    if nets:
        log(f"[docker] 清理残留网络 {len(nets)} 个")
    return len(nets)


def container_running(cid: str) -> bool:
    cp = _run(["inspect", "-f", "{{.State.Running}}", cid], timeout=30, check=False)
    return cp.returncode == 0 and cp.stdout.strip() == "true"


def remove_container(cid_or_name: str) -> None:
    if not cid_or_name:
        return
    _run(["rm", "-f", "-v", cid_or_name], timeout=60, check=False)


def exec_capture(cid: str, argv, timeout=120, workdir: str = None) -> subprocess.CompletedProcess:
    args = ["exec"]
    if workdir:
        args += ["-w", workdir]
    args += [cid] + list(argv)
    return _run(args, timeout=timeout, check=False)


def exec_detached(cid: str, argv) -> None:
    """在容器里后台启动一个进程（不阻塞、不捕获输出）。"""
    _run(["exec", "-d", cid] + list(argv), timeout=60)


def published_port(cid: str, container_port: int):
    """查询容器端口映射到宿主机的地址，返回 (host, port) 或 None。"""
    cp = _run(["port", cid, f"{container_port}/tcp"], timeout=30, check=False)
    if cp.returncode != 0:
        return None
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        host, _, port = line.rpartition(":")
        if port.isdigit():
            return host or "127.0.0.1", int(port)
    return None


def container_log_tail(cid: str, lines: int = 30) -> str:
    cp = _run(["logs", "--tail", str(lines), cid], timeout=30, check=False)
    return (cp.stdout or "") + (cp.stderr or "")


def reap_orphans(log=print) -> int:
    """清理上次异常退出留下的容器（label envtrainer=1）。"""
    cp = _run(["ps", "-aq", "--filter", "label=envtrainer=1"], timeout=30, check=False)
    ids = [x for x in cp.stdout.split() if x]
    for cid in ids:
        remove_container(cid)
    if ids:
        log(f"[docker] 清理残留容器 {len(ids)} 个")
    return len(ids)
