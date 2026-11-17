#!/usr/bin/env bash
# 第 1 关判题：必须在 /work/.venv 内跑通项目自检，且版本锁正确
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }

ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

PY=/work/.venv/bin/python

if [ ! -x "$PY" ]; then
  bad "虚拟环境" "找不到 /work/.venv/bin/python（python -m venv .venv）"
  echo "RESULT|fail"
  exit 1
fi
ok "虚拟环境" ".venv/bin/python 存在"

if "$PY" -c 'import flask, requests' 2>/dev/null; then
  ok "依赖可导入" "flask + requests"
else
  bad "依赖可导入" "venv 里 import flask / requests 失败"
  echo "RESULT|fail"; exit 1
fi

fver=$("$PY" -c 'import flask; print(flask.__version__)' 2>/dev/null)
case "$fver" in
  3.*) ok "Flask 版本" "$fver" ;;
  *)   bad "Flask 版本" "当前 $fver，requirements.txt 要求 3.0.3" ;;
esac

rver=$("$PY" -c 'import requests; print(requests.__version__)' 2>/dev/null)
if [ "$rver" = "2.31.0" ]; then
  ok "requests 版本" "$rver"
else
  bad "requests 版本" "当前 $rver，要求 2.31.0"
fi

if out=$("$PY" app.py --selftest 2>&1) && echo "$out" | grep -q "SELFTEST OK"; then
  ok "项目自检" "$(echo "$out" | grep 'SELFTEST OK' | head -1)"
else
  bad "项目自检" "$(echo "$out" | tail -n 3 | tr '\n' ' ')"
fi

if [ "$fver" != "${fver#3.}" ] && [ "$rver" = "2.31.0" ] && out=$("$PY" app.py --selftest 2>&1) && echo "$out" | grep -q "SELFTEST OK"; then
  echo "RESULT|pass"
  exit 0
fi
echo "RESULT|fail"
exit 1
