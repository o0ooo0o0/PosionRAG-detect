#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 一键部署并启动 Web 演示界面：
#   1. 安装依赖（uv sync，幂等）
#   2. 生成演示数据到 outputs/demo（若缺失；首次需下载模型）
#   3. 启动零依赖 HTTP 服务

uv sync --all-extras

if [ ! -f outputs/demo/rsq-metrics.json ]; then
  echo ">>> 首次运行：生成演示数据（需下载模型，约几分钟）..."
  DEVICE="${DEVICE:-cpu}" bash run_demo.sh
fi

PORT="${PORT:-8000}" exec uv run python web/server.py
