#!/bin/bash
# ============================================================
# AI 文档知识库（MVP）一键启动脚本（Linux / macOS）
# ============================================================
# 功能:
#   1. 检查 Python 3.11+ / Node.js 18+ / MariaDB 可用性
#   2. 检查 backend/.env 是否已配置
#   3. 创建/激活后端虚拟环境
#   4. 创建数据目录
#   5. 后台启动后端 uvicorn（PID 写入 backend/backend.pid）
#   6. 后台启动前端 Vite（PID 写入 frontend/frontend.pid）
#   7. 健康检查并输出启动结果
#
# 约束:
#   - C1 禁用 Docker（本脚本不调用任何 Docker 命令）
#   - C2 MariaDB 本地安装（脚本仅检查服务可用性）
#   - C3 .env 管理敏感配置
# ============================================================

set -e

# ===== 颜色输出 =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===== 路径与配置 =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_PID_FILE="$BACKEND_DIR/backend.pid"
FRONTEND_PID_FILE="$FRONTEND_DIR/frontend.pid"
BACKEND_LOG_DIR="$BACKEND_DIR/data/logs"
FRONTEND_LOG_DIR="$FRONTEND_DIR/data/logs"
BACKEND_LOG_FILE="$BACKEND_LOG_DIR/backend.out.log"
FRONTEND_LOG_FILE="$FRONTEND_LOG_DIR/frontend.out.log"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="5173"

# ===== 工具函数 =====
log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()  { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()   { echo -e "${BLUE}[STEP]${NC} $1"; }

# ===== 1. 环境检查 =====
log_step "1/7 环境检查..."

# ----- Python 环境检测 -----
# 优先级:
#   1. conda 环境 rag-kb（Python 3.11，推荐）
#   2. python3.11 命令
#   3. 系统 python3（仅当版本为 3.11 或 3.12 时）
# 版本约束:
#   - 3.11.x（推荐，开发与测试版本）
#   - 3.12.x（兼容）
#   - 3.13+（拒绝，依赖可能不兼容）
#   - < 3.11（拒绝，版本过低）

CONDA_BIN=""
if [[ -x "/usr/local/soft/miniconda3/bin/conda" ]]; then
    CONDA_BIN="/usr/local/soft/miniconda3/bin/conda"
elif command -v conda &>/dev/null; then
    CONDA_BIN="conda"
fi

PYTHON_ENV_MODE=""
PYTHON_BIN=""
CONDA_ENV_NAME="rag-kb"
CONDA_ENV_PYTHON=""

# 1. 优先检测 conda 环境 rag-kb
if [[ -n "$CONDA_BIN" ]]; then
    if "$CONDA_BIN" env list 2>/dev/null | awk '{print $1}' | grep -qx "$CONDA_ENV_NAME"; then
        # 查找 rag-kb 环境的 python 路径
        CONDA_ENV_PREFIX="$("$CONDA_BIN" info --base 2>/dev/null)/envs/$CONDA_ENV_NAME"
        if [[ ! -x "$CONDA_ENV_PREFIX/bin/python" ]]; then
            # 兼容自定义 envs_dirs
            CONDA_ENV_PREFIX=$("$CONDA_BIN" run -n "$CONDA_ENV_NAME" python -c "import sys; print(sys.prefix)" 2>/dev/null)
        fi
        if [[ -x "$CONDA_ENV_PREFIX/bin/python" ]]; then
            CONDA_ENV_PYTHON="$CONDA_ENV_PREFIX/bin/python"
            PYTHON_ENV_MODE="conda"
            PYTHON_BIN="$CONDA_ENV_PYTHON"
            log_info "Python: $($PYTHON_BIN --version) [conda 环境: $CONDA_ENV_NAME]"
        fi
    fi
fi

# 2. 回退：查找 python3.11 / python3
if [[ -z "$PYTHON_ENV_MODE" ]]; then
    if command -v python3.11 &>/dev/null; then
        PYTHON_BIN="python3.11"
    elif command -v python3 &>/dev/null; then
        PYTHON_BIN="python3"
    else
        log_error "未找到 Python，请先安装 Python 3.11"
        if [[ -n "$CONDA_BIN" ]]; then
            log_error "推荐方案（检测到 conda）："
            log_error "  $CONDA_BIN create -n $CONDA_ENV_NAME python=3.11 -y"
            log_error "  然后重新运行本脚本"
        fi
        exit 1
    fi

    # 版本检查
    PY_VERSION=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -ge 13 ]]; then
        log_error "检测到 Python $PY_VERSION，版本过高（>= 3.13），依赖可能不兼容"
        log_error "项目在 Python 3.11 下开发与测试，依赖（asyncmy/chromadb/sentence-transformers 等）尚未提供 3.13+ 的预编译包"
        log_error ""
        if [[ -n "$CONDA_BIN" ]]; then
            log_error "推荐方案（检测到 conda）："
            log_error "  $CONDA_BIN create -n $CONDA_ENV_NAME python=3.11 -y"
        else
            log_error "请安装 Python 3.11 或 3.12，或使用 conda 创建环境："
            log_error "  conda create -n $CONDA_ENV_NAME python=3.11 -y"
        fi
        log_error "然后重新运行本脚本"
        exit 1
    fi

    if [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 11 ]]; then
        log_error "Python 版本过低: $PY_VERSION，需要 3.11+"
        exit 1
    fi

    PYTHON_ENV_MODE="venv"
    log_info "Python: $($PYTHON_BIN --version) [将创建 .venv]"
    if [[ "$PY_MINOR" -eq 12 ]]; then
        log_warn "Python 3.12 可用但非开发版本，如遇依赖问题请改用 3.11（conda 环境 $CONDA_ENV_NAME）"
    fi
fi

# Node.js 18+
if ! command -v node &>/dev/null; then
    log_error "未找到 Node.js，请先安装 18+"
    exit 1
fi
NODE_VERSION=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
if [[ "$NODE_MAJOR" -lt 18 ]]; then
    log_error "Node.js 版本过低: $NODE_VERSION，需要 18+"
    exit 1
fi
log_info "Node.js: $NODE_VERSION"

# npm
if ! command -v npm &>/dev/null; then
    log_error "未找到 npm，请随 Node.js 一起安装"
    exit 1
fi
log_info "npm: $(npm --version)"

# MariaDB 可用性（仅检查命令存在，不强制要求服务运行——服务可能由系统管理）
if command -v mariadb &>/dev/null; then
    log_info "MariaDB 客户端: $(mariadb --version)"
else
    log_warn "未找到 mariadb 客户端命令，请确认 MariaDB 已安装并运行在 127.0.0.1:3306"
fi

# 端口占用检查
check_port() {
    local port=$1
    local name=$2
    if command -v lsof &>/dev/null; then
        if lsof -i ":$port" -sTCP:LISTEN &>/dev/null; then
            log_warn "端口 $port ($name) 已被占用，可能服务已在运行"
            return 1
        fi
    elif command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep ":$port " &>/dev/null; then
            log_warn "端口 $port ($name) 已被占用，可能服务已在运行"
            return 1
        fi
    fi
    return 0
}
check_port $BACKEND_PORT "后端"
check_port $FRONTEND_PORT "前端"

# ===== 2. 检查 .env =====
log_step "2/7 检查后端 .env 配置..."
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    if [[ -f "$BACKEND_DIR/.env.example" ]]; then
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
        log_warn "已从 .env.example 复制创建 backend/.env"
        log_error "请编辑 backend/.env 填写 DATABASE_URL 与 OPENAI_API_KEY 后重新执行本脚本"
        log_error "  nano $BACKEND_DIR/.env"
        exit 1
    else
        log_error "未找到 backend/.env 与 backend/.env.example"
        exit 1
    fi
else
    # 检查必填项是否仍为占位符
    if grep -q "^OPENAI_API_KEY=sk-xxxxxxxx" "$BACKEND_DIR/.env" || \
       grep -q "^DATABASE_URL=.*:password@" "$BACKEND_DIR/.env"; then
        log_error "backend/.env 仍包含占位符（OPENAI_API_KEY 或 DATABASE_URL 密码未修改）"
        log_error "请编辑 backend/.env 填写真实配置后重新执行本脚本"
        exit 1
    fi
    log_info "backend/.env 已配置"
fi

# ===== 3. Python 环境 =====
log_step "3/7 Python 环境..."

if [[ "$PYTHON_ENV_MODE" == "conda" ]]; then
    # conda 模式：激活 rag-kb 环境
    log_info "激活 conda 环境 $CONDA_ENV_NAME ..."
    # 加载 conda shell 函数
    CONDA_BASE="$("$CONDA_BIN" info --base 2>/dev/null)"
    if [[ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]]; then
        # shellcheck disable=SC1091
        source "$CONDA_BASE/etc/profile.d/conda.sh"
        conda activate "$CONDA_ENV_NAME" 2>/dev/null || {
            # conda activate 失败时直接设置 PATH
            export PATH="$CONDA_BASE/envs/$CONDA_ENV_NAME/bin:$PATH"
            unset PYTHONHOME
        }
    else
        export PATH="$CONDA_BASE/envs/$CONDA_ENV_NAME/bin:$PATH"
        unset PYTHONHOME
    fi
    log_info "Python 路径: $(which python)"
else
    # venv 模式：创建/激活 .venv
    if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
        log_info "创建虚拟环境 .venv ..."
        $PYTHON_BIN -m venv "$BACKEND_DIR/.venv"
    fi
    # 检查 .venv 的 Python 版本是否仍是 3.13+（历史遗留）
    VENV_PY_VERSION=$("$BACKEND_DIR/.venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
    VENV_PY_MINOR=$(echo "$VENV_PY_VERSION" | cut -d. -f2)
    if [[ "$VENV_PY_MINOR" -ge 13 ]]; then
        log_warn "现有 .venv 使用 Python $VENV_PY_VERSION（过高），删除重建..."
        rm -rf "$BACKEND_DIR/.venv"
        $PYTHON_BIN -m venv "$BACKEND_DIR/.venv"
    fi
    # shellcheck disable=SC1091
    source "$BACKEND_DIR/.venv/bin/activate"
    log_info "Python 路径: $(which python)"
fi

# 安装依赖（仅当 fastapi 未安装时）
if ! python -c "import fastapi" &>/dev/null; then
    log_info "安装后端依赖（首次启动较慢，请耐心等待）..."
    # 清理可能损坏的 pip cache（避免 "Cache entry deserialization failed"）
    pip cache purge 2>/dev/null || true
    pip install --upgrade pip --quiet
    pip install -r "$BACKEND_DIR/requirements.txt" --quiet
    log_info "后端依赖安装完成"
else
    log_info "后端依赖已安装"
fi

# ===== 4. 数据目录 =====
log_step "4/7 创建数据目录..."
mkdir -p "$BACKEND_DIR/data/uploads" "$BACKEND_DIR/data/chroma" \
         "$BACKEND_DIR/data/models" "$BACKEND_LOG_DIR"
mkdir -p "$FRONTEND_LOG_DIR"
# 收紧敏感目录权限（SEC-012 建议）
chmod 700 "$BACKEND_DIR/data/chroma" "$BACKEND_DIR/data/uploads" 2>/dev/null || true
log_info "数据目录就绪: backend/data/{uploads,chroma,models,logs}"

# ===== 5. 启动后端 =====
log_step "5/7 启动后端 (uvicorn)..."
cd "$BACKEND_DIR"
# 禁用 chromadb 遥测（chromadb 0.5.0 与新版 posthog 不兼容，
# 会报 "capture() takes 1 positional argument but 3 were given" ERROR 日志，
# 不影响功能但污染日志，且本地部署无需遥测上报）
export ANONYMIZED_TELEMETRY=False
# 后台启动，输出重定向到日志文件
# 使用 setsid 让服务在新会话中运行，脱离 start.sh 的进程组，
# 避免 start.sh 被 SIGTERM 时连带停止服务（如 timeout 到期）
setsid nohup python -m uvicorn app.main:app \
    --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
    > "$BACKEND_LOG_FILE" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
log_info "后端 PID: $BACKEND_PID，日志: $BACKEND_LOG_FILE"

# 等待后端就绪
log_info "等待后端就绪（最多 30 秒）..."
for i in $(seq 1 30); do
    if curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/health" >/dev/null 2>&1; then
        log_info "后端就绪（耗时 ${i}s）"
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        log_error "后端进程已退出，请查看日志: $BACKEND_LOG_FILE"
        tail -n 30 "$BACKEND_LOG_FILE"
        exit 1
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        log_warn "后端 30s 内未响应健康检查，可能仍在启动中（首次加载模型较慢）"
        log_warn "请查看日志确认: tail -f $BACKEND_LOG_FILE"
    fi
done
cd "$SCRIPT_DIR"

# ===== 6. 启动前端 =====
log_step "6/7 启动前端 (Vite)..."
cd "$FRONTEND_DIR"
# 安装依赖（仅当 node_modules 不存在时）
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    log_info "安装前端依赖（首次启动较慢）..."
    npm install --silent
    log_info "前端依赖安装完成"
fi
# 后台启动（使用 setsid 脱离进程组，避免 start.sh 退出时被连带停止）
setsid nohup npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
    > "$FRONTEND_LOG_FILE" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"
log_info "前端 PID: $FRONTEND_PID，日志: $FRONTEND_LOG_FILE"

# 等待前端就绪
log_info "等待前端就绪（最多 20 秒）..."
for i in $(seq 1 20); do
    if curl -sf "http://$FRONTEND_HOST:$FRONTEND_PORT" >/dev/null 2>&1; then
        log_info "前端就绪（耗时 ${i}s）"
        break
    fi
    sleep 1
    if [[ $i -eq 20 ]]; then
        log_warn "前端 20s 内未响应，请查看日志: $FRONTEND_LOG_FILE"
    fi
done
cd "$SCRIPT_DIR"

# ===== 7. 启动完成 =====
log_step "7/7 启动完成"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AI 文档知识库已启动${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  前端:    ${BLUE}http://$FRONTEND_HOST:$FRONTEND_PORT${NC}"
echo -e "  后端:    ${BLUE}http://$BACKEND_HOST:$BACKEND_PORT${NC}"
echo -e "  健康检查: ${BLUE}http://$BACKEND_HOST:$BACKEND_PORT/health${NC}"
echo -e "  API 文档: ${BLUE}http://$BACKEND_HOST:$BACKEND_PORT/docs${NC} ${YELLOW}(仅 DEBUG=true)${NC}"
echo ""
echo -e "  后端 PID: $BACKEND_PID (${BACKEND_PID_FILE})"
echo -e "  前端 PID: $FRONTEND_PID (${FRONTEND_PID_FILE})"
echo ""
echo -e "  日志:"
echo -e "    后端: $BACKEND_LOG_FILE"
echo -e "    前端: $FRONTEND_LOG_FILE"
echo ""
echo -e "  操作:"
echo -e "    停止:    ${BLUE}./stop.sh${NC}"
echo -e "    状态:    ${BLUE}./status.sh${NC}"
echo -e "    健康检查: ${BLUE}./healthcheck.sh${NC}"
echo -e "    重启:    ${BLUE}./restart.sh${NC}"
echo ""
