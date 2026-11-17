#!/usr/bin/env bash
# 第 9 关判题：go.mod / go.sum / 模块缓存三者必须一致，项目能构建能测
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

gf=$(go env GOFLAGS)
ok "构建配置" "GOPROXY=$(go env GOPROXY)  GOFLAGS=${gf:-<空>}"

# 1) go.sum 必须存在且覆盖了 uuid
if [ -f go.sum ] && grep -q 'google/uuid' go.sum; then
  ok "go.sum" "存在，且包含 google/uuid 的校验和（$(wc -l < go.sum) 行）"
else
  bad "go.sum" "缺失或没有 google/uuid 条目"
fi

# 2) 构建
bout=$(go build ./... 2>&1); brc=$?
if [ $brc -eq 0 ]; then
  ok "go build" "通过"
else
  bad "go build" "$(echo "$bout" | head -2 | tr '\n' ' ')"
fi

# 3) 测试
tout=$(go test ./... 2>&1); trc=$?
if [ $trc -eq 0 ] && echo "$tout" | grep -q '^ok'; then
  ok "go test" "$(echo "$tout" | grep '^ok' | head -1)"
else
  bad "go test" "$(echo "$tout" | grep -vE '^\?' | head -3 | tr '\n' ' ')"
fi

# 4) 能跑出结果
rout=$(timeout 30 go run . 2>&1); rrc=$?
if [ $rrc -eq 0 ] && echo "$rout" | grep -qE '^ID: [0-9a-f-]{36}$'; then
  ok "go run" "$(echo "$rout" | head -1)"
else
  bad "go run" "$(echo "$rout" | head -2 | tr '\n' ' ')"
fi

if [ $brc -eq 0 ] && [ $trc -eq 0 ] && [ $rrc -eq 0 ]; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
