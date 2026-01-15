#!/bin/bash
# -*- coding: utf-8 -*-
#
# 服务器端重启脚本
# 在服务器上本地运行，用于重启前后端服务

set -e

# ============================================================================
# 配置（从环境变量或默认值获取）
# ============================================================================

BASE_DIR="${BASE_DIR:-~/iptv_sever}"

# 展开 ~ 符号
BASE_DIR="${BASE_DIR/#\~/$HOME}"

# 脚本路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
START_SCRIPT="$BASE_DIR/start.sh"
STOP_SCRIPT="$BASE_DIR/stop.sh"

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
# 主函数
# ============================================================================

main() {
    log_info "=========================================="
    log_info "重启服务"
    log_info "=========================================="
    echo ""
    
    # 检查脚本是否存在
    if [ ! -f "$STOP_SCRIPT" ]; then
        log_error "停止脚本不存在: $STOP_SCRIPT"
        log_info "请先同步脚本到服务器: ./scripts/sync.sh start_scripts"
        exit 1
    fi
    
    if [ ! -f "$START_SCRIPT" ]; then
        log_error "启动脚本不存在: $START_SCRIPT"
        log_info "请先同步脚本到服务器: ./scripts/sync.sh start_scripts"
        exit 1
    fi
    
    # 1. 停止服务
    log_info "步骤 1/2: 停止服务..."
    echo ""
    if bash "$STOP_SCRIPT"; then
        log_success "服务已停止"
    else
        log_warning "停止服务时出现警告，继续重启..."
    fi
    echo ""
    
    # 等待服务完全停止
    log_info "等待服务完全停止..."
    sleep 2
    
    # 2. 启动服务
    log_info "步骤 2/2: 启动服务..."
    echo ""
    if bash "$START_SCRIPT" "$@"; then
        log_success "服务重启完成"
    else
        log_error "服务启动失败"
        exit 1
    fi
}

# 运行主函数
main "$@"
