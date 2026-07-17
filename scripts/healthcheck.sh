#!/bin/bash
# ============================================================
# AI 文档知识库（MVP）健康检查脚本（Linux / macOS）
# ============================================================
# 检查项:
#   1. 后端 /health 端点
#   2. 前端 HTTP 可达
#   3. MariaDB 端口监听
#   4. Chroma 数据文件存在
#   5. 日志目录可写
#   6. 磁盘空间
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="5173"

PASS=0
FAIL=0
WARN=0

ok()    { echo -e "  ${GREEN}[OK]${NC}   $1"; PASS=$((PASS+1)); }
fail()  { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
warn()  { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARN=$((WARN+1)); }

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 健康检查开始"
echo "================================"

# 1. 后端健康检查
echo ""
echo "1. 后端服务"
if curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/health" -o /tmp/health_resp 2>/dev/null; then
    ok "后端 /health 响应: $(cat /tmp/health_resp)"
else
    fail "后端 /health 不可达 (http://$BACKEND_HOST:$BACKEND_PORT/health)"
fi
rm -f /tmp/health_resp

# 2. 前端可达
echo ""
echo "2. 前端服务"
if curl -sf -o /dev/null -w "%{http_code}" "http://$FRONTEND_HOST:$FRONTEND_PORT" 2>/dev/null | grep -q "200"; then
    ok "前端主页可访问 (http://$FRONTEND_HOST:$FRONTEND_PORT)"
else
    fail "前端主页不可达 (http://$FRONTEND_HOST:$FRONTEND_PORT)"
fi

# 3. MariaDB
echo ""
echo "3. MariaDB 数据库"
if command -v mariadb &>/dev/null; then
    # 检查端口
    if command -v lsof &>/dev/null && lsof -i :3306 -sTCP:LISTEN >/dev/null 2>&1; then
        ok "MariaDB 端口 3306 监听中"
    elif command -v ss &>/dev/null && ss -tln 2>/dev/null | grep ":3306 " >/dev/null; then
        ok "MariaDB 端口 3306 监听中"
    else
        warn "MariaDB 端口 3306 未监听（可能服务未启动，或使用 socket 连接）"
    fi
    # 尝试连接（不传密码，仅测试 socket 连接）
    if mariadb -e "SELECT 1" >/dev/null 2>&1; then
        ok "MariaDB socket 连接可用（无密码）"
    else
        warn "MariaDB socket 连接需要密码（属正常配置）"
    fi
else
    warn "未找到 mariadb 命令，跳过数据库检查"
fi

# 4. Chroma 数据
echo ""
echo "4. Chroma 向量库"
CHROMA_DIR="$SCRIPT_DIR/backend/data/chroma"
if [[ -d "$CHROMA_DIR" ]]; then
    if [[ -f "$CHROMA_DIR/chroma.sqlite3" ]]; then
        SIZE=$(du -h "$CHROMA_DIR/chroma.sqlite3" | cut -f1)
        ok "Chroma 数据存在: chroma.sqlite3 ($SIZE)"
    else
        warn "Chroma 目录存在但无 sqlite3 文件（可能尚未上传文档）"
    fi
else
    warn "Chroma 目录不存在: $CHROMA_DIR（首次启动时由后端创建）"
fi

# 5. 日志目录
echo ""
echo "5. 日志目录"
LOG_DIR="$SCRIPT_DIR/backend/data/logs"
if [[ -d "$LOG_DIR" ]]; then
    if [[ -w "$LOG_DIR" ]]; then
        ok "日志目录可写: $LOG_DIR"
        # 统计最近错误（精确匹配日志级别，避免误报 SQL 列名 error_message）
        if [[ -f "$LOG_DIR/backend.out.log" ]]; then
            # 匹配 [ERROR] / [CRITICAL] 级别日志，以及 Python Traceback 头
            # 排除 SQL echo 中的 error_message 列名、error_message 参数值
            ALL_ERR_COUNT=$(grep -cE "\[ERROR\]|\[CRITICAL\]|^Traceback \(most recent" "$LOG_DIR/backend.out.log" 2>/dev/null || echo 0)
            # 统计 chromadb 遥测错误（chromadb 0.5.0 与新版 posthog 不兼容，已知无害，不影响功能）
            TELEMETRY_ERR_COUNT=$(grep -cE "\[ERROR\] chromadb\.telemetry\.product\.posthog" "$LOG_DIR/backend.out.log" 2>/dev/null || echo 0)
            # 需要关注的真正错误
            ERR_COUNT=$((ALL_ERR_COUNT - TELEMETRY_ERR_COUNT))
            if [[ "$ERR_COUNT" -eq 0 ]]; then
                if [[ "$TELEMETRY_ERR_COUNT" -gt 0 ]]; then
                    ok "后端日志无错误记录（已忽略 $TELEMETRY_ERR_COUNT 条 chromadb 遥测错误，不影响功能）"
                else
                    ok "后端日志无错误记录"
                fi
            else
                warn "后端日志发现 $ERR_COUNT 条错误/异常记录（已忽略 $TELEMETRY_ERR_COUNT 条 chromadb 遥测错误）："
                grep -E "\[ERROR\]|\[CRITICAL\]|^Traceback \(most recent" "$LOG_DIR/backend.out.log" | grep -v "chromadb\.telemetry\.product\.posthog" | tail -10 | sed 's/^/        /'
            fi
        fi
    else
        fail "日志目录不可写: $LOG_DIR"
    fi
else
    warn "日志目录不存在: $LOG_DIR（启动 start.sh 时会自动创建）"
fi

# 6. 磁盘空间
echo ""
echo "6. 磁盘空间"
DISK_USAGE=$(df -h "$SCRIPT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [[ -n "$DISK_USAGE" ]]; then
    if [[ "$DISK_USAGE" -lt 85 ]]; then
        ok "磁盘使用率: ${DISK_USAGE}% (< 85%)"
    else
        fail "磁盘使用率过高: ${DISK_USAGE}% (>= 85%)"
    fi
fi

# 总结
echo ""
echo "================================"
TOTAL=$((PASS+FAIL+WARN))
echo "健康检查完成: $PASS/$TOTAL 通过, $WARN 警告, $FAIL 失败"
if [[ "$FAIL" -gt 0 ]]; then
    echo -e "${RED}存在失败项，请检查后重试${NC}"
    exit 1
else
    echo -e "${GREEN}健康检查通过${NC}"
    exit 0
fi
echo ""
