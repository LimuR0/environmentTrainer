#!/usr/bin/env bash
# 第 6 关判题：必须真正用 GCC 14 编出来，并且跑出正确结果
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

# 1) 编译器就绪
v14=$(g++-14 -dumpversion 2>/dev/null)
vdef=$(g++ -dumpversion 2>/dev/null)
if [ -n "$v14" ]; then
  ok "g++-14" "$v14"
else
  bad "g++-14" "未安装（dpkg -i /opt/debs/*.deb 或 apt-get install g++-14）"
fi

# 2) 产物存在
if [ -x build/app ]; then
  ok "构建产物" "build/app"
else
  bad "构建产物" "没有 build/app（make CXX=g++-14）"
fi

# 3) 运行时输出
out=$(timeout 20 ./build/app 2>&1); rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q "COMPUTE OK 4.00"; then
  ok "运行结果" "$(echo "$out" | grep 'COMPUTE OK' | head -1)"
else
  bad "运行结果" "$(echo "$out" | tail -2 | tr '\n' ' ')"
fi

# 4) 确认是 GCC 14 编的（不是偷偷改代码绕开 <print>）
if [ -x build/app ] && strings build/app 2>/dev/null | grep -q "GCC: (Ubuntu 14"; then
  ok "编译器标记" "二进制里带 GCC 14 标记"
else
  bad "编译器标记" "产物不是 GCC 14 编的（strings build/app | grep 'GCC: '）"
fi

if [ -x build/app ] && echo "$out" | grep -q "COMPUTE OK 4.00" \
   && strings build/app 2>/dev/null | grep -q "GCC: (Ubuntu 14"; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
