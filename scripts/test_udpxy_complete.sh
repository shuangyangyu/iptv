#!/bin/bash
# -*- coding: utf-8 -*-
#
# UDPXY 完整测试脚本
# 检查权限、启动、进程状态等
#
# 用法: ./test_udpxy_complete.sh

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
# 配置
# ============================================================================

UDPXY_BINARY="/usr/local/bin/udpxy"
UDPXY_PORT=4022
UDPXY_BIND="0.0.0.0"
UDPXY_IFACE="ens192"
UDPXY_MAX_CONN=5
UDPXY_LOG="/var/log/udpxy.log"
UDPXY_PID="/tmp/udpxy.pid"
API_URL="http://localhost:8088/api/v1/udpxy"

# ============================================================================
# 辅助函数
# ============================================================================

# 检查命令是否存在
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 检查文件权限
check_file_permission() {
    local file="$1"
    local need_write="$2"
    
    if [ ! -e "$file" ]; then
        # 文件不存在，检查父目录
        local dir=$(dirname "$file")
        if [ ! -d "$dir" ]; then
            log_warning "目录不存在: $dir"
            return 1
        fi
        
        if [ "$need_write" = "true" ]; then
            if [ -w "$dir" ]; then
                log_success "目录可写: $dir"
                return 0
            else
                log_error "目录不可写: $dir"
                return 1
            fi
        else
            log_info "目录存在: $dir"
            return 0
        fi
    else
        if [ "$need_write" = "true" ]; then
            if [ -w "$file" ]; then
                log_success "文件可写: $file"
                return 0
            else
                log_error "文件不可写: $file"
                return 1
            fi
        else
            log_info "文件存在: $file"
            return 0
        fi
    fi
}

# 检查进程
check_process() {
    local pid="$1"
    if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 检查僵尸进程
check_zombie() {
    if ps aux | grep -E '\[udpxy\] <defunct>' >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 清理进程
cleanup() {
    log_info "清理 UDPXY 进程..."
    pkill -9 udpxy 2>/dev/null || true
    rm -f "$UDPXY_PID"
    sleep 1
}

# ============================================================================
# 测试步骤
# ============================================================================

test_1_check_environment() {
    log_info "=========================================="
    log_info "步骤 1: 检查环境"
    log_info "=========================================="
    echo ""
    
    # 检查当前用户
    log_info "当前用户: $(whoami)"
    log_info "用户 ID: $(id -u)"
    echo ""
    
    # 检查 UDPXY 可执行文件
    if [ -f "$UDPXY_BINARY" ] && [ -x "$UDPXY_BINARY" ]; then
        log_success "UDPXY 可执行文件存在: $UDPXY_BINARY"
        ls -l "$UDPXY_BINARY"
    else
        log_error "UDPXY 可执行文件不存在或不可执行: $UDPXY_BINARY"
        return 1
    fi
    echo ""
    
    # 检查日志文件权限
    log_info "检查日志文件权限: $UDPXY_LOG"
    if check_file_permission "$UDPXY_LOG" "true"; then
        log_success "可以使用日志文件: $UDPXY_LOG"
        USE_LOG=true
    else
        log_warning "无法写入日志文件: $UDPXY_LOG"
        log_info "将使用用户目录下的日志文件: ~/udpxy.log"
        UDPXY_LOG="$HOME/udpxy.log"
        USE_LOG=true
    fi
    echo ""
    
    # 检查 PID 文件目录
    log_info "检查 PID 文件目录: $(dirname $UDPXY_PID)"
    if check_file_permission "$UDPXY_PID" "true"; then
        log_success "可以使用 PID 文件: $UDPXY_PID"
    else
        log_error "无法写入 PID 文件: $UDPXY_PID"
        return 1
    fi
    echo ""
    
    # 检查 API 服务
    log_info "检查 API 服务..."
    if curl -s "$API_URL/status" >/dev/null 2>&1; then
        log_success "API 服务运行中"
    else
        log_warning "API 服务未运行，将跳过 API 测试"
        API_AVAILABLE=false
    fi
    echo ""
}

test_2_manual_start() {
    log_info "=========================================="
    log_info "步骤 2: 手动启动测试（不使用日志文件）"
    log_info "=========================================="
    echo ""
    
    cleanup
    
    log_info "启动命令: $UDPXY_BINARY -p $UDPXY_PORT -a $UDPXY_BIND -m $UDPXY_IFACE -c $UDPXY_MAX_CONN"
    $UDPXY_BINARY -p $UDPXY_PORT -a $UDPXY_BIND -m $UDPXY_IFACE -c $UDPXY_MAX_CONN >/dev/null 2>&1 &
    local pid=$!
    echo "$pid" > "$UDPXY_PID"
    
    log_info "等待进程启动..."
    sleep 3
    
    if check_process "$pid"; then
        log_success "进程运行中 (PID: $pid)"
        ps aux | grep "$pid" | grep -v grep
        echo ""
        
        # 检查端口
        log_info "检查端口监听..."
        if lsof -i :$UDPXY_PORT >/dev/null 2>&1; then
            log_success "端口 $UDPXY_PORT 正在监听"
            lsof -i :$UDPXY_PORT | head -3
        else
            log_error "端口 $UDPXY_PORT 未监听"
        fi
        echo ""
        
        # 检查僵尸进程
        log_info "检查僵尸进程..."
        if check_zombie; then
            log_error "发现僵尸进程！"
            ps aux | grep defunct | grep udpxy
        else
            log_success "未发现僵尸进程"
        fi
        echo ""
        
        # 停止进程
        log_info "停止进程..."
        kill "$pid" 2>/dev/null || true
        sleep 1
        if check_process "$pid"; then
            log_warning "进程未停止，强制终止..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$UDPXY_PID"
        log_success "进程已停止"
    else
        log_error "进程启动失败或立即退出"
        return 1
    fi
    echo ""
}

test_3_manual_start_with_log() {
    log_info "=========================================="
    log_info "步骤 3: 手动启动测试（使用日志文件）"
    log_info "=========================================="
    echo ""
    
    cleanup
    
    # 确保日志目录存在
    local log_dir=$(dirname "$UDPXY_LOG")
    if [ ! -d "$log_dir" ]; then
        log_info "创建日志目录: $log_dir"
        mkdir -p "$log_dir" 2>/dev/null || {
            log_warning "无法创建日志目录，跳过此测试"
            return 0
        }
    fi
    
    log_info "启动命令: $UDPXY_BINARY -p $UDPXY_PORT -a $UDPXY_BIND -m $UDPXY_IFACE -c $UDPXY_MAX_CONN -l $UDPXY_LOG"
    $UDPXY_BINARY -p $UDPXY_PORT -a $UDPXY_BIND -m $UDPXY_IFACE -c $UDPXY_MAX_CONN -l "$UDPXY_LOG" >/dev/null 2>&1 &
    local pid=$!
    echo "$pid" > "$UDPXY_PID"
    
    log_info "等待进程启动..."
    sleep 3
    
    if check_process "$pid"; then
        log_success "进程运行中 (PID: $pid)"
        echo ""
        
        # 检查日志文件
        if [ -f "$UDPXY_LOG" ]; then
            log_success "日志文件已创建: $UDPXY_LOG"
            log_info "日志内容（最后5行）:"
            tail -5 "$UDPXY_LOG" 2>/dev/null || echo "无法读取日志"
        else
            log_warning "日志文件未创建: $UDPXY_LOG"
        fi
        echo ""
        
        # 停止进程
        log_info "停止进程..."
        kill "$pid" 2>/dev/null || true
        sleep 1
        rm -f "$UDPXY_PID"
        log_success "进程已停止"
    else
        log_error "进程启动失败"
        log_info "检查日志文件错误信息..."
        if [ -f "$UDPXY_LOG" ]; then
            tail -10 "$UDPXY_LOG" 2>/dev/null || true
        fi
        return 1
    fi
    echo ""
}

test_4_api_start() {
    if [ "$API_AVAILABLE" = "false" ]; then
        log_warning "跳过 API 测试（API 服务未运行）"
        return 0
    fi
    
    log_info "=========================================="
    log_info "步骤 4: API 启动测试"
    log_info "=========================================="
    echo ""
    
    cleanup
    
    log_info "通过 API 启动 UDPXY..."
    local response=$(curl -s -X POST "$API_URL/start")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo ""
    
    log_info "等待进程启动..."
    sleep 4
    
    # 检查 PID 文件
    if [ -f "$UDPXY_PID" ]; then
        local pid=$(cat "$UDPXY_PID")
        log_info "PID 文件中的 PID: $pid"
        
        if check_process "$pid"; then
            log_success "进程运行中 (PID: $pid)"
            ps aux | grep "$pid" | grep -v grep
            echo ""
            
            # 检查端口
            if lsof -i :$UDPXY_PORT >/dev/null 2>&1; then
                log_success "端口 $UDPXY_PORT 正在监听"
                lsof -i :$UDPXY_PORT | head -3
            else
                log_error "端口 $UDPXY_PORT 未监听"
            fi
            echo ""
            
            # 检查僵尸进程
            log_info "检查僵尸进程..."
            if check_zombie; then
                log_error "发现僵尸进程！"
                ps aux | grep defunct | grep udpxy
            else
                log_success "未发现僵尸进程"
            fi
            echo ""
            
            # 获取状态
            log_info "获取 API 状态..."
            curl -s "$API_URL/status" | python3 -m json.tool 2>/dev/null | head -12
            echo ""
        else
            log_error "进程不存在 (PID: $pid)"
            log_info "检查进程是否立即退出..."
            ps aux | grep udpxy | grep -v grep || echo "未找到 udpxy 进程"
        fi
    else
        log_error "PID 文件不存在"
    fi
    echo ""
}

test_5_api_restart() {
    if [ "$API_AVAILABLE" = "false" ]; then
        return 0
    fi
    
    log_info "=========================================="
    log_info "步骤 5: API 重启测试"
    log_info "=========================================="
    echo ""
    
    log_info "通过 API 重启 UDPXY..."
    local response=$(curl -s -X POST "$API_URL/restart")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo ""
    
    log_info "等待进程重启..."
    sleep 4
    
    # 检查进程
    if [ -f "$UDPXY_PID" ]; then
        local pid=$(cat "$UDPXY_PID")
        if check_process "$pid"; then
            log_success "进程运行中 (PID: $pid)"
        else
            log_error "进程不存在"
        fi
    fi
    
    # 检查僵尸进程
    log_info "检查僵尸进程..."
    if check_zombie; then
        log_error "发现僵尸进程！"
        ps aux | grep defunct | grep udpxy
    else
        log_success "未发现僵尸进程"
    fi
    echo ""
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    log_info "=========================================="
    log_info "UDPXY 完整测试"
    log_info "=========================================="
    echo ""
    
    API_AVAILABLE=true
    USE_LOG=false
    
    # 执行测试
    test_1_check_environment || {
        log_error "环境检查失败"
        exit 1
    }
    
    test_2_manual_start || {
        log_warning "手动启动测试失败（不使用日志）"
    }
    
    test_3_manual_start_with_log || {
        log_warning "手动启动测试失败（使用日志）"
    }
    
    test_4_api_start || {
        log_warning "API 启动测试失败"
    }
    
    test_5_api_restart || {
        log_warning "API 重启测试失败"
    }
    
    # 最终清理
    cleanup
    
    log_success "=========================================="
    log_success "测试完成"
    log_success "=========================================="
    echo ""
    log_info "如果日志文件权限有问题，可以："
    log_info "  1. 使用 sudo 创建日志文件: sudo touch $UDPXY_LOG && sudo chown \$USER:\$USER $UDPXY_LOG"
    log_info "  2. 或者修改配置使用用户目录下的日志文件: ~/udpxy.log"
    echo ""
}

# 执行主函数
main "$@"
