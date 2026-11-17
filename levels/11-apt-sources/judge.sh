#!/usr/bin/env bash
# 第 11 关判题：apt 源必须格式正确，cowsay 要能跑
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

SRC="/etc/apt/sources.list /etc/apt/sources.list.d/*"
srcs=$(grep -hs '^deb ' $SRC 2>/dev/null)
if [ -z "$srcs" ]; then
  bad "apt 源" "没有可用的 deb 行"
else
  # 每行都必须带组件（main / contrib / non-free...）
  badline=$(echo "$srcs" | awk '{ if (NF < 4 || $4 ~ /^\[/) next; if (NF < 4) print }')
  if echo "$srcs" | grep -qE '^deb .* (main|contrib|non-free)'; then
    ok "apt 源" "$(echo "$srcs" | head -1)"
  else
    bad "apt 源" "缺少组件（main/contrib）：$(echo "$srcs" | head -1)"
  fi
fi

# 索引能不能正常读
if out=$(apt-get update 2>&1); then
  ok "apt 索引" "apt-get update 成功"
  UPDATED=1
else
  if echo "$out" | grep -qiE "malformed|does not have a Release file|could not be read"; then
    bad "apt 索引" "$(echo "$out" | grep -iE 'E:' | head -1)"
    UPDATED=0
  else
    UPDATED=0
    ok "apt 索引" "非源问题导致（离线？）"
  fi
fi

if apt-get check >/dev/null 2>&1; then
  ok "dpkg 状态" "apt-get check 通过"
else
  bad "dpkg 状态" "$(apt-get check 2>&1 | grep -E '^E:' | head -1)"
fi

COW=""
command -v cowsay >/dev/null 2>&1 && COW="$(command -v cowsay)"
[ -z "$COW" ] && [ -x /usr/games/cowsay ] && COW="/usr/games/cowsay"
if [ -n "$COW" ]; then
  ok "cowsay 已安装" "$COW"
  if "$COW" hello 2>&1 | grep -q "hello"; then
    ok "cowsay 可运行" "输出正常"
  else
    bad "cowsay 可运行" "运行失败"
  fi
else
  bad "cowsay 已安装" "找不到 cowsay（apt-get install -y cowsay）"
fi

if [ "${UPDATED:-0}" = "1" ] && [ -n "$COW" ] && echo "$srcs" | grep -qE ' (main|contrib|non-free)'; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
