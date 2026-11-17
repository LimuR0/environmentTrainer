#!/usr/bin/env bash
# 项目启动脚本（依赖 node >= 20.6 的 --env-file）
set -e
exec node --env-file=.env index.js
