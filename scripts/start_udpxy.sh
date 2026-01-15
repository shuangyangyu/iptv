#!/bin/bash
# -*- coding: utf-8 -*-
#
# UDPXY 启动脚本
# 手动启动 UDPXY 服务

set -e

# ============================================================================
# 配置（可根据需要修改）
# ============================================================================

UDPXY_PORT="${UDPXY_PORT:-4022}"
UDPXY_BIND="${UDPXY_BIND:-0.0.0.0}"
UDPXY_SOURCE_IFACE="${UDPXY_SOURCE_IFACE:-eth1}"
UDPXY_MAX_CONN="${UDPXY_MAX_CONN:-1000}"
UDPXY_LOG="${UDPXY_LOG:-/var/log/udpxy.log}"

# ============================================================================
# 颜色输出
# ============================================================================

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

# 检查 UDPXY 是否已安装
check_udpxy_installed() {
    if ! command -v udpxy >/dev/null 2>&1; then
        # 检查常见路径
        if [ ! -f "/usr/local/bin/udpxy" ] && [ ! -f "/usr/bin/udpxy" ]; then
            log_error "UDPXY 未安装"
            log_info "请先运行: ./setup_server.sh"
            return 1
        fi
    fi
    return 0
}

# 检查 UDPXY 是否已在运行
check_udpxy_running() {
    local pids=$(pgrep -f "udpxy.*-p.*$UDPXY_PORT" 2>/dev/null || echo "")
    if [ -n "$pids" ]; then
        log_warning "UDPXY 已在运行 (PID: $pids)"
        ps aux | grep -E "udpxy.*-p.*$UDPXY_PORT" | grep -v grep || true
        return 0
    fi
    return 1
}

# 启动 UDPXY
start_udpxy() {
    log_info "启动 UDPXY..."
    log_info "  端口: $UDPXY_PORT"
    log_info "  绑定地址: $UDPXY_BIND"
    log_info "  源网卡: $UDPXY_SOURCE_IFACE"
    log_info "  最大连接数: $UDPXY_MAX_CONN"
    log_info "  日志文件: $UDPXY_LOG"
    echo ""
    
    # 确保日志目录存在
    local log_dir=$(dirname "$UDPXY_LOG")
    if [ ! -d "$log_dir" ]; then
        log_info "创建日志目录: $log_dir"
        sudo mkdir -p "$log_dir" 2>/dev/null || mkdir -p "$log_dir"
    fi
    
    # 查找 udpxy 命令
    local udpxy_cmd=""
    if command -v udpxy >/dev/null 2>&1; then
        udpxy_cmd="udpxy"
    elif [ -f "/usr/local/bin/udpxy" ]; then
        udpxy_cmd="/usr/local/bin/udpxy"
    elif [ -f "/usr/bin/udpxy" ]; then
        udpxy_cmd="/usr/bin/udpxy"
    else
        log_error "未找到 UDPXY 程序"
        return 1
    fi
    
    log_info "使用 UDPXY: $udpxy_cmd"
    
    # 构建命令
    local cmd="$udpxy_cmd -p $UDPXY_PORT -a $UDPXY_BIND -m $UDPXY_SOURCE_IFACE -c $UDPXY_MAX_CONN"
    
    if [ -n "$UDPXY_LOG" ]; then
        cmd="$cmd -l $UDPXY_LOG"
    fi
    
    # 启动 UDPXY（后台运行）
    log_info "执行命令: $cmd"
    nohup $cmd > /dev/null 2>&1 &
    local pid=$!
    
    # 等待一下，检查是否启动成功
    sleep 1
    
    if ps -p $pid > /dev/null 2>&1; then
        log_success "UDPXY 启动成功 (PID: $pid)"
        log_info "检查进程:"
        ps aux | grep -E "udpxy.*-p.*$UDPXY_PORT" | grep -v grep || true
        echo ""
        log_info "检查端口监听:"
        lsof -i :$UDPXY_PORT 2>/dev/null || netstat -tlnp | grep :$UDPXY_PORT || true
        return 0
    else
        log_error "UDPXY 启动失败"
        log_info "请检查日志: $UDPXY_LOG"
        return 1
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    log_info "=========================================="
    log_info "UDPXY 启动脚本"
    log_info "=========================================="
    echo ""
    
    # 检查是否已安装
    if ! check_udpxy_installed; then
        exit 1
    fi
    
    # 检查是否已在运行
    if check_udpxy_running; then
        log_info "UDPXY 已在运行，无需重复启动"
        exit 0
    fi
    
    # 启动 UDPXY
    if start_udpxy; then
        log_success "=========================================="
        log_success "UDPXY 启动完成"
        log_success "=========================================="
        echo ""
        log_info "使用以下命令检查状态:"
        log_info "  pgrep -af udpxy"
        log_info "  lsof -i :$UDPXY_PORT"
        log_info "  curl http://$UDPXY_BIND:$UDPXY_PORT/status"
    else
        log_error "UDPXY 启动失败"
        exit 1
    fi
}

# 运行主函数
main "$@"
