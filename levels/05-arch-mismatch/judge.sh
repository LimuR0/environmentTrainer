#!/usr/bin/env bash
# 第 5 关判题：vendor 库必须与本机架构一致，且功能正确
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

here=$(uname -m)
case "$here" in
  aarch64|arm64) want="AArch64" ;;
  x86_64|amd64)  want="X86-64" ;;
  *)             want="" ;;
esac
ok "本机架构" "$here"

if [ ! -f vendor/libmath.so ]; then
  bad "vendor 库" "vendor/libmath.so 不存在"
  echo "RESULT|fail"; exit 1
fi

machine=$(readelf -h vendor/libmath.so 2>/dev/null | awk -F: '/Machine/{gsub(/^ +/,"",$2); print $2}')
if echo "$machine" | grep -q "$want"; then
  ok "库架构" "$machine（与本机一致）"
else
  bad "库架构" "$machine（本机是 $here）"
fi

out=$(python3 - <<'EOF' 2>&1
import ctypes, os, sys
try:
    lib = ctypes.CDLL(os.path.abspath("vendor/libmath.so"))
    lib.magic_avg.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
    lib.magic_avg.restype = ctypes.c_double
    arr = (ctypes.c_double * 5)(1.0, 2.0, 3.0, 4.0, 10.0)
    v = lib.magic_avg(arr, 5)
    print(f"magic_avg={v:.4f}")
    sys.exit(0 if abs(v - 4.0) < 1e-9 else 5)
except OSError as e:
    print(f"加载失败: {e}")
    sys.exit(6)
EOF
)
if [ $? -eq 0 ] && echo "$out" | grep -q "magic_avg=4.0000"; then
  ok "库功能" "$(echo "$out" | tail -1)"
else
  bad "库功能" "$(echo "$out" | tail -1)"
fi

cout=$(./check.sh 2>&1); crc=$?
if [ $crc -eq 0 ] && echo "$cout" | grep -q "MATH OK 4.0000"; then
  ok "check.sh" "MATH OK 4.0000"
else
  bad "check.sh" "$(echo "$cout" | tail -2 | tr '\n' ' ')"
fi

if echo "$machine" | grep -q "$want" && echo "$out" | grep -q "magic_avg=4.0000" && [ $crc -eq 0 ]; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
