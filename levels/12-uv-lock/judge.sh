#!/usr/bin/env bash
# 第 12 关判题：lock 与 pyproject 必须一致，且按 lock 装出来的环境能跑测试
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

if ! command -v uv >/dev/null 2>&1; then
  bad "uv" "找不到 uv 命令"
  echo "RESULT|fail"; exit 1
fi
ok "uv" "$(uv --version 2>&1 | head -1)"

# 1) lock 是否与 pyproject 一致
lout=$(uv lock --check 2>&1); lrc=$?
if [ $lrc -eq 0 ]; then
  ok "lock 一致性" "uv lock --check 通过"
else
  bad "lock 一致性" "$(echo "$lout" | grep -iE 'outdated|needs to be updated|error' | head -1)"
fi

# 2) lock 里要有 httpx
if grep -q 'name = "httpx"' uv.lock 2>/dev/null; then
  ok "lock 内容" "uv.lock 里包含 httpx"
else
  bad "lock 内容" "uv.lock 里没有 httpx（pyproject 加了但没重新 lock）"
fi

# 3) 模拟 CI：--frozen 装环境，再用 --no-sync 跑测试（测试不能靠 uv run 现场补依赖）
sout=$(uv sync --frozen 2>&1); src=$?
if [ $src -eq 0 ]; then
  ok "uv sync --frozen" "按 lock 装完（$(echo "$sout" | grep -cE '^ \+' ) 个包）"
else
  bad "uv sync --frozen" "$(echo "$sout" | tail -2 | tr '\n' ' ')"
fi

tout=$(uv run --no-sync pytest -q 2>&1); trc=$?
if [ $trc -eq 0 ]; then
  ok "pytest（--no-sync）" "$(echo "$tout" | tail -1)"
else
  bad "pytest（--no-sync）" "$(echo "$tout" | grep -E 'ModuleNotFoundError|error|FAILED' | head -1)"
fi

hv=$(uv run --no-sync python -c "import httpx; print(httpx.__version__)" 2>&1 | tail -1)
if [ "$hv" = "0.27.2" ]; then
  ok "运行时依赖" "httpx $hv"
else
  bad "运行时依赖" "httpx 不可用：$hv"
fi

if [ $lrc -eq 0 ] && [ $src -eq 0 ] && [ $trc -eq 0 ] && [ "$hv" = "0.27.2" ]; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
