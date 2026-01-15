#!/bin/bash
# -*- coding: utf-8 -*-
#
# 服务器端启动脚本
# 在服务器上本地运行，用于启动前后端服务

set -e

# ============================================================================
# 配置（从环境变量或默认值获取）
# ============================================================================

BASE_DIR="${BASE_DIR:-~/iptv_sever}"
VENV_DIR="${VENV_DIR:-$BASE_DIR/venv}"
API_DIR="${API_DIR:-$BASE_DIR/api}"
BACKEND_DIR="${BACKEND_DIR:-$BASE_DIR/backend}"
API_PORT="${API_PORT:-8088}"
API_HOST="${API_HOST:-0.0.0.0}"

# 展开 ~ 符号
BASE_DIR="${BASE_DIR/#\~/$HOME}"
VENV_DIR="${VENV_DIR/#\~/$HOME}"
API_DIR="${API_DIR/#\~/$HOME}"
BACKEND_DIR="${BACKEND_DIR/#\~/$HOME}"

# ============================================================================
# 日志函数
# ============================================================================

# 颜色输出
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# 检查函数
# ============================================================================

# 检查服务是否已运行
check_running() {
    if pgrep -f 'uvicorn.*api.main:app' >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 检查虚拟环境
check_venv() {
    if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
        log_error "虚拟环境不存在: $VENV_DIR"
        log_info "请先运行: bash $BASE_DIR/setup_server.sh"
        return 1
    fi
    return 0
}

# 检查 API 目录
check_api_dir() {
    if [ ! -d "$API_DIR" ]; then
        log_error "API 目录不存在: $API_DIR"
        return 1
    fi
    return 0
}

# ============================================================================
# 启动函数
# ============================================================================

# 停止现有服务
stop_existing() {
    if check_running; then
        log_warning "检测到服务已在运行，先停止..."
        pkill -f 'uvicorn.*api.main:app' >/dev/null 2>&1
        sleep 2
        
        # 确认是否停止
        if check_running; then
            log_warning "强制停止服务..."
            pkill -9 -f 'uvicorn.*api.main:app' >/dev/null 2>&1
            sleep 1
        fi
    fi
}

# 启动服务
start_service() {
    local daemon="${1:-true}"
    
    log_info "启动 FastAPI 服务..."
    log_info "  工作目录: $BASE_DIR"
    log_info "  虚拟环境: $VENV_DIR"
    log_info "  API 目录: $API_DIR"
    log_info "  监听地址: $API_HOST:$API_PORT"
    echo ""
    
    # 检查前置条件
    if ! check_venv; then
        exit 1
    fi
    
    if ! check_api_dir; then
        exit 1
    fi
    
    # 确保 __init__.py 存在（用于 Python 包识别）
    if [ ! -f "$BASE_DIR/__init__.py" ]; then
        log_info "创建 __init__.py 文件..."
        cat > "$BASE_DIR/__init__.py" << 'EOF'
"""
IPTV Server - IPTV M3U/EPG 生成工具

主要模块：
- backend: 核心业务逻辑（频道处理、M3U/EPG 生成）
- web: Flask Web 控制台
"""
EOF
    fi
    
    # 停止现有服务
    stop_existing
    
    # 构建启动命令
    # 从 iptv_sever 目录运行，设置 PYTHONPATH 包含父目录
    # 这样 Python 可以将 iptv_sever 作为包，api 和 backend 作为同级子包
    local venv_activate="$VENV_DIR/bin/activate"
    local venv_python="$VENV_DIR/bin/python"
    local parent_dir=$(dirname "$BASE_DIR")
    local base_dir_name=$(basename "$BASE_DIR")
    # 设置 PYTHONPATH，将父目录添加到路径，这样可以使用 iptv_sever.api.main
    local cmd="cd $BASE_DIR && source $venv_activate && export PYTHONPATH=$parent_dir:\$PYTHONPATH && $venv_python -m uvicorn $base_dir_name.api.main:app --host $API_HOST --port $API_PORT --reload --reload-dir $API_DIR --reload-dir $BACKEND_DIR --log-level info"
    
    if [ "$daemon" = "true" ]; then
        # 后台运行
        log_info "后台启动服务..."
        nohup bash -c "$cmd" > "$BASE_DIR/api.log" 2>&1 &
        local pid=$!
        sleep 2
        
        # 检查是否启动成功
        if check_running; then
            log_success "服务已启动（后台运行，PID: $pid）"
            log_info "查看日志: tail -f $BASE_DIR/api.log"
            log_info "访问地址: http://$API_HOST:$API_PORT"
            log_info "停止服务: bash $BASE_DIR/stop.sh"
        else
            log_error "服务启动失败，请查看日志:"
            tail -20 "$BASE_DIR/api.log" 2>/dev/null || true
            exit 1
        fi
    else
        # 前台运行
        log_info "前台启动服务（按 Ctrl+C 停止）..."
        log_info "访问地址: http://$API_HOST:$API_PORT"
        echo ""
        bash -c "$cmd"
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    log_info "=========================================="
    log_info "启动服务"
    log_info "=========================================="
    echo ""
    
    # 解析参数
    local daemon="true"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --foreground|-f)
                daemon="false"
                shift
                ;;
            --daemon|-d)
                daemon="true"
                shift
                ;;
            *)
                log_warning "未知参数: $1"
                shift
                ;;
        esac
    done
    
    start_service "$daemon"
}

# 运行主函数
main "$@"
