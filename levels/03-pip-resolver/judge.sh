#!/usr/bin/env bash
# 第 3 关判题：隔离环境里依赖自洽 + 项目自检通过
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

PY=/work/.venv/bin/python
PIP=/work/.venv/bin/pip

if [ ! -x "$PY" ]; then
  bad "虚拟环境" "找不到 /work/.venv/bin/python"
  echo "RESULT|fail"; exit 1
fi
ok "虚拟环境" ".venv 存在"

if "$PY" -c 'import fastapi, pydantic, httpx' 2>/dev/null; then
  ok "依赖可导入" "fastapi + pydantic + httpx"
else
  bad "依赖可导入" "$("$PY" -c 'import fastapi, pydantic, httpx' 2>&1 | tail -1)"
  echo "RESULT|fail"; exit 1
fi

fver=$("$PY" -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null)
pver=$("$PY" -c 'import pydantic; print(pydantic.VERSION)' 2>/dev/null)
if [ "${pver%%.*}" = "2" ]; then
  ok "pydantic 版本" "$pver（v2，model_dump 可用）"
else
  bad "pydantic 版本" "当前 $pver，代码使用 pydantic v2 API"
fi

case "$fver" in
  0.11[0-9].*|0.1[2-9][0-9].*|1.*) ok "fastapi 版本" "$fver（支持 pydantic v2）" ;;
  *) bad "fastapi 版本" "当前 $fver，0.100 只支持 pydantic<2，需要 >=0.115" ;;
esac

check=$("$PIP" check 2>&1)
if [ -z "$check" ] || echo "$check" | grep -q "No broken requirements"; then
  ok "依赖树完整" "pip check 无 broken requirements"
else
  bad "依赖树完整" "$(echo "$check" | head -3 | tr '\n' ' ')"
fi

out=$("$PY" app.py --selftest 2>&1)
if echo "$out" | grep -q "SELFTEST OK"; then
  ok "项目自检" "$(echo "$out" | grep 'SELFTEST OK' | head -1)"
  echo "RESULT|pass"; exit 0
else
  bad "项目自检" "$(echo "$out" | tail -3 | tr '\n' ' ')"
fi

echo "RESULT|fail"; exit 1
