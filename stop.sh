#!/bin/bash
# ============================================================
# AI 文档知识库（MVP）一键停止脚本（Linux / macOS）
# ============================================================
# 通过 PID 文件优雅停止前后端，超时后强制 kill
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID_FILE="$SCRIPT_DIR/backend/backend.pid"
FRONTEND_PID_FILE="$SCRIPT_DIR/frontend/frontend.pid"

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()  { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()   { echo -e "${BLUE}[STEP]${NC} $1"; }

# 优雅停止进程：先 SIGTERM，等 10s，仍存活则 SIGKILL
stop_process() {
    local pid_file=$1
    local name=$2

    if [[ ! -f "$pid_file" ]]; then
        log_warn "$name PID 文件不存在（$pid_file），可能未启动"
        return 0
    fi

    local pid
    pid=$(cat "$pid_file")
    if ! kill -0 "$pid" 2>/dev/null; then
        log_info "$name 进程 $pid 已不存在"
        rm -f "$pid_file"
        return 0
    fi

    log_info "停止 $name (PID: $pid)..."
    kill -TERM "$pid" 2>/dev/null || true

    for i in $(seq 1 10); do
        if ! kill -0 "$pid" 2>/dev/null; then
            log_info "$name 已停止"
            rm -f "$pid_file"
            return 0
        fi
        sleep 1
    done

    log_warn "$name 10s 内未退出，强制 kill"
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$pid_file"
    log_info "$name 已强制停止"
}

log_step "停止 AI 文档知识库服务..."
stop_process "$FRONTEND_PID_FILE" "前端"
stop_process "$BACKEND_PID_FILE" "后端"

# 兜底：按端口查找并停止（针对 PID 文件丢失的情况）
log_step "端口兜底清理..."
for port in 5173 8000; do
    if command -v lsof &>/dev/null; then
        pids=$(lsof -ti :$port -sTCP:LISTEN 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            log_warn "端口 $port 仍有进程占用: $pids，尝试停止"
            for p in $pids; do
                kill -TERM "$p" 2>/dev/null || true
            done
            sleep 2
            for p in $pids; do
                if kill -0 "$p" 2>/dev/null; then
                    kill -9 "$p" 2>/dev/null || true
                fi
            done
        fi
    fi
done

echo ""
log_info "所有服务已停止"
echo ""
