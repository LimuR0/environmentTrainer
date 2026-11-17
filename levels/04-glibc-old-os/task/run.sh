#!/usr/bin/env bash
# 项目启动脚本
# TODO: vendor/ 里那份是 CI 在 Ubuntu 24.04 编译的产物，本机跑不了。
set -e
exec ./vendor/tool "$@"
