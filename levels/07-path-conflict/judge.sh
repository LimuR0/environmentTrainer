#!/usr/bin/env bash
# 第 7 关判题：交互 shell 里的 node 必须是 20，且 run.sh 能跑通
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

# 用交互式 shell 判，这样 ~/.bashrc 里的 PATH 修改才生效
nv=$(bash -ic 'node -v' 2>/dev/null | tr -d '\r' | grep -E '^v[0-9]+' | tail -1)
np=$(bash -ic 'command -v node' 2>/dev/null | tr -d '\r' | tail -1)

if [ -n "$nv" ]; then
  major=$(echo "$nv" | sed 's/^v//; s/\..*//')
  if [ "${major:-0}" -ge 20 ]; then
    ok "node 版本" "$nv（$np）"
  else
    bad "node 版本" "$nv（$np），需要 >= 20"
  fi
else
  bad "node 版本" "交互 shell 里读不到 node"
fi

out=$(bash -ic 'cd /work && ./run.sh' 2>&1); rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q "STARTED"; then
  ok "启动脚本" "$(echo "$out" | grep 'STARTED' | head -1)"
else
  bad "启动脚本" "$(echo "$out" | grep -v '^\[' | tail -2 | tr '\n' ' ')"
fi

if [ -n "$nv" ] && [ "${major:-0}" -ge 20 ] && [ $rc -eq 0 ] && echo "$out" | grep -q "STARTED"; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
