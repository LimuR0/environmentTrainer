#!/usr/bin/env bash
# 第 10 关判题：依赖收敛 + 测试通过
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

# 1) commons-lang3 在依赖树里只能出现一个版本
mvn -o -B dependency:tree -Dverbose -Dincludes=org.apache.commons:commons-lang3 \
    -DoutputFile=/tmp/tree.txt >/dev/null 2>&1
versions=$(grep -o 'commons-lang3:jar:[0-9.]*' /tmp/tree.txt 2>/dev/null | sed 's/.*://' | sort -u)
count=$(echo "$versions" | grep -c .)
if [ "$count" = "1" ]; then
  ok "依赖收敛" "commons-lang3 只有一个版本 $versions"
elif [ "$count" = "0" ]; then
  bad "依赖收敛" "读不到依赖树（mvn 命令本身失败了？）"
else
  bad "依赖收敛" "commons-lang3 有 ${count} 个版本：$(echo "$versions" | tr '\n' ' ')"
fi

# 2) enforcer + 测试
out=$(mvn -o -B test 2>&1); rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q "BUILD SUCCESS"; then
  ok "mvn test" "BUILD SUCCESS"
else
  reason=$(echo "$out" | grep -E "Dependency convergence error|Tests run:.*Failures: [1-9]|BUILD FAILURE" | head -2 | tr '\n' ' ')
  bad "mvn test" "${reason:-mvn 返回 $rc}"
fi

# 3) 测试真的跑了且全过
summary=$(echo "$out" | grep -E "Tests run: [0-9]+, Failures" | tail -1 | sed 's/^\[INFO\] *//; s/^\[ERROR\] *//')
if echo "$out" | grep -qE "Tests run: [1-9][0-9]*, Failures: 0, Errors: 0"; then
  ok "单元测试" "$summary"
else
  bad "单元测试" "${summary:-没有测试被执行}"
fi

if [ "$count" = "1" ] && [ $rc -eq 0 ]; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
