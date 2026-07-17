#!/bin/bash
# ============================================================
# AI 文档知识库（MVP）一键重启脚本（Linux / macOS）
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "重启 AI 文档知识库服务..."
"$SCRIPT_DIR/stop.sh"
sleep 2
"$SCRIPT_DIR/start.sh"
