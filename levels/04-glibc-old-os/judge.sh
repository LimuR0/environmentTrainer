#!/usr/bin/env bash
# 第 4 关判题：必须在当前系统上跑通，且实际使用的二进制不能要求更高版本的 glibc
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }
ver_of() { objdump -T "$1" 2>/dev/null | grep -o 'GLIBC_2\.[0-9]*' | sed 's/GLIBC_//' | sort -Vu | tail -1; }

hostv=$(ldd --version 2>/dev/null | head -1 | grep -o '[0-9]\+\.[0-9]*$')
if [ -n "$hostv" ]; then ok "本机 glibc" "$hostv"; else bad "本机 glibc" "读不到版本"; fi

needv=$(ver_of vendor/tool)
if [ -n "$needv" ]; then
  ok "CI 产物要求" "GLIBC_$needv（在新系统上编的）"
else
  ok "CI 产物要求" "已被替换或无法解析"
fi

# 1) 启动脚本能否跑通
out=$(timeout 20 ./run.sh 2>&1); rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q "TOOL OK: v1.4"; then
  ok "启动脚本" "./run.sh -> TOOL OK: v1.4"
else
  bad "启动脚本" "$(echo "$out" | tail -2 | tr '\n' ' ')"
fi

# 2) 找出 run.sh 实际执行的那个文件
target=""
for cand in build/tool vendor/tool; do
  if [ -x "$cand" ] && grep -q "$cand" run.sh 2>/dev/null; then target="$cand"; break; fi
done
if [ -z "$target" ]; then
  if [ -x build/tool ]; then target="build/tool"; elif [ -x vendor/tool ]; then target="vendor/tool"; fi
fi

if [ -n "$target" ]; then
  tv=$(ver_of "$target")
  if [ -z "$tv" ]; then
    ok "实际执行的产物" "$target（静态或无法解析版本）"
  else
    top=$(printf '%s\n%s\n' "$tv" "$hostv" | sort -V | tail -1)
    if [ "$top" = "$tv" ] && [ "$tv" != "$hostv" ]; then
      bad "实际执行的产物" "$target 要 GLIBC_$tv > 本机 $hostv"
    else
      ok "实际执行的产物" "$target 依赖 GLIBC_$tv（<= 本机 $hostv）"
    fi
  fi
else
  bad "实际执行的产物" "没有找到可执行的产物"
fi

# 3) 有过本机重编译（vendor/tool 被换成旧版本也算）
if [ -x build/tool ] || { [ -n "$needv" ] && [ "$(ver_of vendor/tool)" != "$needv" ]; }; then
  ok "本机重编译" "存在本机编译的产物"
else
  bad "本机重编译" "没有本机编译产物（make build）"
fi

tv=$(ver_of "$target")
top=$(printf '%s\n%s\n' "$tv" "$hostv" | sort -V | tail -1)
if [ $rc -eq 0 ] && echo "$out" | grep -q "TOOL OK: v1.4" && [ -n "$target" ] \
   && { [ -z "$tv" ] || [ "$top" != "$tv" ] || [ "$tv" = "$hostv" ]; }; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
