"""自动挑选最快的包镜像源（apt / pip / npm / go）。

用途：
  1. 构建镜像时通过 --build-arg 注入，避免从国外源慢慢拉
  2. 容器运行时也受益（apt 源、pip.conf、.npmrc 会写进镜像）

选择结果缓存在项目根目录的 .mirrors.json（已 gitignore），7 天内复用；
`python start.py --mirrors` 可以强制重新探测。
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import statistics
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, ".mirrors.json")
CACHE_TTL = 7 * 24 * 3600

# 每个类别：候选站点 -> (显示名, 探测 URL, 注入值)
CANDIDATES = {
    "apt": [
        ("aliyun", "https://mirrors.aliyun.com/debian/dists/bookworm/Release"),
        ("huawei", "https://repo.huaweicloud.com/debian/dists/bookworm/Release"),
        ("ustc", "https://mirrors.ustc.edu.cn/debian/dists/bookworm/Release"),
        ("tuna", "https://mirrors.tuna.tsinghua.edu.cn/debian/dists/bookworm/Release"),
        ("official", "http://deb.debian.org/debian/dists/bookworm/Release"),
    ],
    "pip": [
        ("ustc", "https://mirrors.ustc.edu.cn/pypi/simple/requests/"),
        ("aliyun", "https://mirrors.aliyun.com/pypi/simple/requests/"),
        ("tuna", "https://pypi.tuna.tsinghua.edu.cn/simple/requests/"),
        ("official", "https://pypi.org/simple/requests/"),
    ],
    "npm": [
        ("npmmirror", "https://registry.npmmirror.com/react"),
        ("official", "https://registry.npmjs.org/react"),
    ],
    "go": [
        ("goproxy.cn", "https://goproxy.cn/github.com/google/uuid/@v/list"),
        ("goproxy.io", "https://goproxy.io/github.com/google/uuid/@v/list"),
        ("official", "https://proxy.golang.org/github.com/google/uuid/@v/list"),
    ],
}

# 选中的站点 -> 实际注入到 Dockerfile / 环境变量的值
APT_BASE = {
    "aliyun": "https://mirrors.aliyun.com",
    "huawei": "https://repo.huaweicloud.com",
    "ustc": "https://mirrors.ustc.edu.cn",
    "tuna": "https://mirrors.tuna.tsinghua.edu.cn",
    "official": "",
}
PIP_INDEX = {
    "ustc": "https://mirrors.ustc.edu.cn/pypi/simple",
    "aliyun": "https://mirrors.aliyun.com/pypi/simple",
    "tuna": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "official": "https://pypi.org/simple",
}
NPM_REGISTRY = {
    "npmmirror": "https://registry.npmmirror.com",
    "official": "https://registry.npmjs.org",
}
GO_PROXY = {
    "goproxy.cn": "https://goproxy.cn,direct",
    "goproxy.io": "https://goproxy.io,direct",
    "official": "https://proxy.golang.org,direct",
}


def _probe(url, tries=3, timeout=6):
    times = []
    for _ in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp.read(1)
            times.append(time.time() - t0)
        except Exception:
            return None
    return statistics.median(times)


def probe_all(log=None):
    """并发探测所有候选，返回每类最快的站点（全部失败时退回官方源）。"""
    result = {}
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        for kind, items in CANDIDATES.items():
            futures = {pool.submit(_probe, url): name for name, url in items}
            timings = {}
            for fut, name in futures.items():
                try:
                    t = fut.result()
                except Exception:
                    t = None
                if t is not None:
                    timings[name] = t
            if timings:
                best = min(timings, key=timings.get)
                result[kind] = {
                    "name": best,
                    "latency_ms": round(timings[best] * 1000),
                    "all": {k: round(v * 1000) for k, v in sorted(timings.items(), key=lambda x: x[1])},
                }
                if log:
                    log(f"  {kind:4} -> {best} ({result[kind]['latency_ms']}ms)")
            else:
                result[kind] = {"name": "official", "latency_ms": None, "all": {}}
                if log:
                    log(f"  {kind:4} -> 官方源（其它候选都不可达）")
    return result


def load_or_pick(force=False, log=None):
    if not force and os.path.isfile(CACHE_PATH):
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("picked_at", 0) < CACHE_TTL and data.get("mirrors"):
                return data["mirrors"]
        except Exception:
            pass
    mirrors = probe_all(log=log)
    payload = {"picked_at": time.time(), "mirrors": mirrors}
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CACHE_PATH)
    return mirrors


def build_args(mirrors=None):
    """转成 docker build --build-arg 需要的键值；没有可用镜像时返回空（用官方源）。"""
    if mirrors is None:
        if not os.path.isfile(CACHE_PATH):
            return {}
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                mirrors = json.load(f).get("mirrors", {})
        except Exception:
            return {}
    args = {}
    apt = mirrors.get("apt", {}).get("name")
    if apt and APT_BASE.get(apt):
        args["APT_MIRROR"] = APT_BASE[apt]
    pip = mirrors.get("pip", {}).get("name")
    if pip and PIP_INDEX.get(pip):
        args["PIP_INDEX_URL"] = PIP_INDEX[pip]
    npm = mirrors.get("npm", {}).get("name")
    if npm and NPM_REGISTRY.get(npm):
        args["NPM_REGISTRY"] = NPM_REGISTRY[npm]
    gop = mirrors.get("go", {}).get("name")
    if gop and GO_PROXY.get(gop):
        args["GO_MIRROR"] = GO_PROXY[gop]
    return args


def summary(mirrors=None):
    """给 --check 用的一行摘要。"""
    args = build_args(mirrors)
    if not args:
        return "镜像源：未配置（用官方源）"
    parts = []
    if "APT_MIRROR" in args:
        parts.append("apt=" + args["APT_MIRROR"].split("//")[-1])
    if "PIP_INDEX_URL" in args:
        parts.append("pip=" + args["PIP_INDEX_URL"].split("//")[-1].split("/")[0])
    if "NPM_REGISTRY" in args:
        parts.append("npm=" + args["NPM_REGISTRY"].split("//")[-1])
    if "GO_MIRROR" in args:
        parts.append("go=" + args["GO_MIRROR"].split(",")[0].split("//")[-1])
    return "镜像源：" + "  ".join(parts)
