#!/usr/bin/env python3
"""课程项目：需要 requests 才能跑。
装不上包的时候，这个文件连 import 都会失败。
"""
import sys

import requests


def selftest() -> int:
    print("SELFTEST OK requests", requests.__version__)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("requests", requests.__version__)
