#!/usr/bin/env python3
"""课程示例项目：一个最小 Flask 服务。

注意：它用的是 Flask 3.x 的 API（flask.json.provider.DefaultJSONProvider），
在 Flask 2.x 上会直接 ImportError —— 这正是本关要你解决的问题。
"""
from __future__ import annotations

import sys

from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider

import requests


class Utf8JSONProvider(DefaultJSONProvider):
    ensure_ascii = False


app = Flask(__name__)
app.json = Utf8JSONProvider(app)


@app.get("/health")
def health():
    import flask

    return jsonify(
        status="ok",
        flask=flask.__version__,
        requests=requests.__version__,
    )


def selftest() -> int:
    with app.test_client() as client:
        resp = client.get("/health")
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        body = resp.get_json()
        assert body["status"] == "ok", body
        assert body["flask"].startswith("3."), f"Flask 版本不对: {body['flask']}"
        assert body["requests"] == "2.31.0", f"requests 版本不对: {body['requests']}"
    print("SELFTEST OK", f"flask={body['flask']}", f"requests={body['requests']}")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    app.run(host="0.0.0.0", port=5000)
