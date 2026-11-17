#!/usr/bin/env bash
# 项目健康检查：先看架构对不对，再真正加载库跑一遍
set -u
SO="${1:-vendor/libmath.so}"

if [ ! -f "$SO" ]; then
  echo "✗ 找不到 $SO" >&2
  exit 2
fi

machine=$(readelf -h "$SO" 2>/dev/null | awk -F: '/Machine/{gsub(/^ +/,"",$2); print $2}')
here=$(uname -m)
case "$here" in
  aarch64|arm64) want="AArch64" ;;
  x86_64|amd64)  want="X86-64" ;;
  *)             want="" ;;
esac

echo "库架构 : $machine"
echo "本机   : $here"

case "$machine" in
  *"$want"*) ;;
  *)
    echo "✗ incompatible architecture: 这个 .so 是给 $machine 编的，本机是 $here" >&2
    echo "  release 页面上只有 x86_64 的构建（aarch64 只有源码包）" >&2
    exit 3
    ;;
esac

python3 - "$SO" <<'EOF'
import ctypes, sys, os

path = os.path.abspath(sys.argv[1])
lib = ctypes.CDLL(path)
lib.magic_avg.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
lib.magic_avg.restype = ctypes.c_double

arr = (ctypes.c_double * 5)(1.0, 2.0, 3.0, 4.0, 10.0)
val = lib.magic_avg(arr, 5)
print(f"MATH OK {val:.4f}")
sys.exit(0 if abs(val - 4.0) < 1e-9 else 4)
EOF
