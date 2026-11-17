# envdemo (uv)

用 [uv](https://docs.astral.sh/uv/) 管理依赖。

```bash
uv lock          # 解析依赖，写 uv.lock
uv sync          # 按 lock 建 .venv
uv run pytest    # 在项目环境里跑测试
```

CI 里用的是 `uv sync --frozen`（lock 必须已提交且与 pyproject 一致）。

> 现在 CI 挂了：本地加了 httpx 但忘记更新 lock。
