#!/bin/bash
# -*- coding: utf-8 -*-
#
# 服务器端停止脚本
# 在服务器上本地运行，用于停止前后端服务

set -e

# ============================================================================
# 配置（从环境变量或默认值获取）
# ============================================================================

BASE_DIR="${BASE_DIR:-~/iptv_sever}"

# 展开 ~ 符号
BASE_DIR="${BASE_DIR/#\~/$HOME}"

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
# 停止函数
# ============================================================================

# 查找并停止服务
stop_service() {
    log_info "查找运行中的服务..."
    
    # 查找后端服务进程
    local pids=$(pgrep -f 'uvicorn.*api.main:app' 2>/dev/null || echo "")
    
    if [ -z "$pids" ]; then
        log_warning "未找到运行中的服务"
        return 0
    fi
    
    log_info "找到进程: $pids"
    log_info "停止服务..."
    
    # 停止服务
    pkill -f 'uvicorn.*api.main:app' >/dev/null 2>&1
    sleep 2
    
    # 确认是否停止
    local remaining=$(pgrep -f 'uvicorn.*api.main:app' 2>/dev/null || echo "")
    if [ -z "$remaining" ]; then
        log_success "服务已停止"
        return 0
    else
        log_warning "部分进程可能仍在运行，强制停止..."
        pkill -9 -f 'uvicorn.*api.main:app' >/dev/null 2>&1
        sleep 1
        
        # 再次确认
        remaining=$(pgrep -f 'uvicorn.*api.main:app' 2>/dev/null || echo "")
        if [ -z "$remaining" ]; then
            log_success "服务已强制停止"
            return 0
        else
            log_error "无法停止服务，进程仍在运行: $remaining"
            return 1
        fi
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    log_info "=========================================="
    log_info "停止服务"
    log_info "=========================================="
    echo ""
    
    stop_service
}

# 运行主函数
main "$@"
