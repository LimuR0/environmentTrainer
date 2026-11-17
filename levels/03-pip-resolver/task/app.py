#!/usr/bin/env python3
"""课程项目：一个最小的 FastAPI 服务（pydantic v2 风格）。

注意：这里用了 pydantic v2 的 `model_dump()`，
所以 pydantic 1.x 装上来会直接报 AttributeError，
而 fastapi 0.100 又只支持 pydantic<2 —— 这就是要解的冲突。
"""
from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    qty: int


app = FastAPI(title="env-trainer-demo")


@app.post("/items")
def create_item(item: Item):
    data = item.model_dump()          # pydantic v2 API
    return {"ok": True, **data, "double": data["qty"] * 2}


@app.get("/health")
def health():
    import fastapi
    import pydantic

    return {"status": "ok", "fastapi": fastapi.__version__, "pydantic": pydantic.VERSION}


def selftest() -> int:
    client = TestClient(app)

    resp = client.post("/items", json={"name": "pen", "qty": 3})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["double"] == 6, body

    h = client.get("/health").json()
    assert h["pydantic"].startswith("2."), f"需要 pydantic v2，当前 {h['pydantic']}"

    print("SELFTEST OK", "fastapi=" + h["fastapi"], "pydantic=" + h["pydantic"])
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
