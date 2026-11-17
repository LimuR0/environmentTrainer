#!/usr/bin/env bash
# macOS / Linux 启动脚本（真正的逻辑在 start.py，三平台共用）
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else
    echo "找不到 python3，请先安装 Python 3.9+（macOS: brew install python@3.12 / Linux: apt install python3）" >&2
    exit 1
  fi
fi
exec "$PY" start.py "$@"
