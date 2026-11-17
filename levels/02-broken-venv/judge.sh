#!/usr/bin/env bash
# 第 2 关判题：虚拟环境必须自洽可用
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

if [ ! -x tool/bin/python ]; then
  bad "python 可执行" "tool/bin/python 不存在或不可执行"
  echo "RESULT|fail"; exit 1
fi
ok "python 可执行" "$(./tool/bin/python -V 2>&1)"

if [ ! -x tool/bin/pip ]; then
  bad "pip 可执行" "tool/bin/pip 不存在或不可执行"
  echo "RESULT|fail"; exit 1
fi

pipout=$(./tool/bin/pip --version 2>&1)
if [ $? -ne 0 ]; then
  bad "pip 可执行" "$(echo "$pipout" | tail -1)"
else
  ok "pip 可执行" "$pipout"
fi

if echo "$pipout" | grep -q "/work/tool"; then
  ok "pip 路径" "指向 /work/tool"
else
  bad "pip 路径" "仍是 $(echo "$pipout" | grep -o '/[^ ]*tool' | head -1)"
fi

prefix=$(./tool/bin/python -c 'import sys; print(sys.prefix)' 2>&1)
if [ "$prefix" = "/work/tool" ]; then
  ok "虚拟环境自洽" "sys.prefix=/work/tool"
else
  bad "虚拟环境自洽" "sys.prefix=$prefix，应为 /work/tool"
fi

cver=$(./tool/bin/python -c 'import click; print(click.__version__)' 2>&1)
if [ "$cver" = "8.1.7" ]; then
  ok "依赖可用" "click $cver"
else
  bad "依赖可用" "import click 失败：$(echo "$cver" | tail -1)"
fi

if [ "$prefix" = "/work/tool" ] && [ "$cver" = "8.1.7" ] && echo "$pipout" | grep -q "/work/tool"; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
