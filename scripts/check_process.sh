#!/bin/bash
# -*- coding: utf-8 -*-
#
# 进程检查脚本
# 用于检查各种进程是否运行

set -e

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

# 方法 1: 使用 pgrep 检查进程
check_process_pgrep() {
    local process_name="$1"
    
    if [ -z "$process_name" ]; then
        log_error "请提供进程名称"
        return 1
    fi
    
    log_info "使用 pgrep 检查进程: $process_name"
    
    local pids=$(pgrep -f "$process_name" 2>/dev/null || echo "")
    
    if [ -n "$pids" ]; then
        log_success "进程运行中 (PID: $pids)"
        # 显示详细信息
        ps aux | grep -E "$process_name" | grep -v grep || true
        return 0
    else
        log_warning "进程未运行"
        return 1
    fi
}

# 方法 2: 使用 pidof 检查进程
check_process_pidof() {
    local process_name="$1"
    
    if [ -z "$process_name" ]; then
        log_error "请提供进程名称"
        return 1
    fi
    
    log_info "使用 pidof 检查进程: $process_name"
    
    local pid=$(pidof "$process_name" 2>/dev/null || echo "")
    
    if [ -n "$pid" ]; then
        log_success "进程运行中 (PID: $pid)"
        ps -p "$pid" -o pid,ppid,cmd,etime,stat || true
        return 0
    else
        log_warning "进程未运行"
        return 1
    fi
}

# 方法 3: 使用 lsof 检查端口
check_port() {
    local port="$1"
    
    if [ -z "$port" ]; then
        log_error "请提供端口号"
        return 1
    fi
    
    log_info "检查端口 $port 是否被占用..."
    
    if command -v lsof >/dev/null 2>&1; then
        local result=$(lsof -i :"$port" 2>/dev/null || echo "")
        if [ -n "$result" ]; then
            log_success "端口 $port 被占用:"
            echo "$result"
            return 0
        else
            log_warning "端口 $port 未被占用"
            return 1
        fi
    else
        log_warning "lsof 命令未安装，无法检查端口"
        return 1
    fi
}

# 方法 4: 检查 PID 文件
check_pid_file() {
    local pid_file="$1"
    
    if [ -z "$pid_file" ]; then
        log_error "请提供 PID 文件路径"
        return 1
    fi
    
    log_info "检查 PID 文件: $pid_file"
    
    if [ ! -f "$pid_file" ]; then
        log_warning "PID 文件不存在"
        return 1
    fi
    
    local pid=$(cat "$pid_file" 2>/dev/null || echo "")
    
    if [ -z "$pid" ]; then
        log_warning "PID 文件为空"
        return 1
    fi
    
    if ps -p "$pid" > /dev/null 2>&1; then
        log_success "进程运行中 (PID: $pid)"
        ps -p "$pid" -o pid,ppid,cmd,etime,stat || true
        return 0
    else
        log_warning "PID 文件存在，但进程未运行 (PID: $pid)"
        return 1
    fi
}

# 综合检查函数
check_process() {
    local process_name="$1"
    local method="${2:-pgrep}"  # 默认使用 pgrep
    
    if [ -z "$process_name" ]; then
        log_error "请提供进程名称"
        echo ""
        echo "用法: $0 <进程名> [方法]"
        echo ""
        echo "方法选项:"
        echo "  pgrep  - 使用 pgrep 命令（默认）"
        echo "  pidof  - 使用 pidof 命令"
        echo "  port   - 检查端口占用（需要提供端口号）"
        echo "  pidfile - 检查 PID 文件（需要提供文件路径）"
        echo ""
        echo "示例:"
        echo "  $0 udpxy"
        echo "  $0 udpxy pidof"
        echo "  $0 '' port 4022"
        echo "  $0 '' pidfile /tmp/udpxy.pid"
        return 1
    fi
    
    case "$method" in
        pgrep)
            check_process_pgrep "$process_name"
            ;;
        pidof)
            check_process_pidof "$process_name"
            ;;
        port)
            check_port "$process_name"  # 这里 process_name 实际是端口号
            ;;
        pidfile)
            check_pid_file "$process_name"  # 这里 process_name 实际是文件路径
            ;;
        *)
            log_error "未知的方法: $method"
            return 1
            ;;
    esac
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    if [ $# -eq 0 ]; then
        echo "进程检查工具"
        echo ""
        echo "用法: $0 <进程名> [方法]"
        echo ""
        echo "常用检查:"
        echo "  $0 udpxy              # 检查 UDPXY 进程"
        echo "  $0 uvicorn            # 检查 API 服务进程"
        echo "  $0 'uvicorn.*api.main:app'  # 检查完整命令"
        echo ""
        echo "检查端口:"
        echo "  $0 '' port 4022       # 检查 UDPXY 端口"
        echo "  $0 '' port 8088       # 检查 API 端口"
        echo ""
        echo "检查 PID 文件:"
        echo "  $0 '' pidfile /tmp/udpxy.pid"
        echo ""
        exit 0
    fi
    
    local process_name="$1"
    local method="${2:-pgrep}"
    
    check_process "$process_name" "$method"
}

# 运行主函数
main "$@"
