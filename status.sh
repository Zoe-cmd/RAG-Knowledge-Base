#!/bin/bash
# ============================================================
# AI 文档知识库（MVP）状态查看脚本（Linux / macOS）
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID_FILE="$SCRIPT_DIR/backend/backend.pid"
FRONTEND_PID_FILE="$SCRIPT_DIR/frontend/frontend.pid"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="5173"

# 检查 PID 是否存活
check_pid() {
    local pid_file=$1
    local name=$2
    if [[ ! -f "$pid_file" ]]; then
        echo -e "  ${RED}●${NC} $name: 未启动（无 PID 文件）"
        return 1
    fi
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "  ${GREEN}●${NC} $name: 运行中 (PID: $pid)"
        return 0
    else
        echo -e "  ${YELLOW}●${NC} $name: PID 文件存在但进程已退出 (PID: $pid)"
        return 1
    fi
}

# 检查端口监听
check_port() {
    local port=$1
    local name=$2
    if command -v lsof &>/dev/null; then
        if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1; then
            return 0
        fi
    elif command -v ss &>/dev/null; then
        if ss -tln 2>/dev/null | grep ":$port " >/dev/null; then
            return 0
        fi
    fi
    return 1
}

# 检查 HTTP 健康
check_http() {
    local url=$1
    curl -sf "$url" >/dev/null 2>&1
}

echo ""
echo "AI 文档知识库运行状态"
echo "======================"
echo ""

echo "进程状态:"
check_pid "$BACKEND_PID_FILE" "后端"
check_pid "$FRONTEND_PID_FILE" "前端"
echo ""

echo "端口监听:"
if check_port $BACKEND_PORT "后端"; then
    echo -e "  ${GREEN}●${NC} :$BACKEND_PORT (后端) 监听中"
else
    echo -e "  ${RED}●${NC} :$BACKEND_PORT (后端) 未监听"
fi
if check_port $FRONTEND_PORT "前端"; then
    echo -e "  ${GREEN}●${NC} :$FRONTEND_PORT (前端) 监听中"
else
    echo -e "  ${RED}●${NC} :$FRONTEND_PORT (前端) 未监听"
fi
echo ""

echo "HTTP 健康:"
if check_http "http://$BACKEND_HOST:$BACKEND_PORT/health"; then
    echo -e "  ${GREEN}●${NC} 后端 /health: $(curl -s "http://$BACKEND_HOST:$BACKEND_PORT/health")"
else
    echo -e "  ${RED}●${NC} 后端 /health: 不可达"
fi
if check_http "http://$FRONTEND_HOST:$FRONTEND_PORT"; then
    echo -e "  ${GREEN}●${NC} 前端主页: 可访问"
else
    echo -e "  ${RED}●${NC} 前端主页: 不可达"
fi
echo ""

echo "访问地址:"
echo -e "  前端: http://$FRONTEND_HOST:$FRONTEND_PORT"
echo -e "  后端: http://$BACKEND_HOST:$BACKEND_PORT"
echo -e "  健康: http://$BACKEND_HOST:$BACKEND_PORT/health"
echo ""
