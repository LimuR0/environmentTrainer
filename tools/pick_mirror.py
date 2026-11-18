#!/usr/bin/env python3
"""探测并选择最快的包镜像源。

    python tools/pick_mirror.py            # 探测并写入 .mirrors.json
    python tools/pick_mirror.py --show     # 只看当前缓存
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))

import mirrors  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="只显示当前缓存")
    args = ap.parse_args()

    if args.show:
        if not os.path.isfile(mirrors.CACHE_PATH):
            print("还没有探测结果，先跑一次 python tools/pick_mirror.py")
            return 1
        with open(mirrors.CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print()
        print(mirrors.summary(data.get("mirrors")))
        return 0

    print("正在探测镜像站…")
    result = mirrors.load_or_pick(force=True, log=print)
    print()
    for kind, info in result.items():
        ranked = ", ".join(f"{k}={v}ms" for k, v in info.get("all", {}).items())
        print(f"{kind:4} 选中 {info['name']}")
        if ranked:
            print(f"     全部：{ranked}")
    print()
    print("写入", mirrors.CACHE_PATH)
    print(mirrors.summary(result))
    print("\n下次构建镜像会自动带上这些源（--build-arg）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
