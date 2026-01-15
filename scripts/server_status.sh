#!/bin/bash
# -*- coding: utf-8 -*-
#
# 服务器端状态检查脚本
# 在服务器上本地运行，用于检查服务状态、端口监听和日志

set -e

# ============================================================================
# 配置（从环境变量或默认值获取）
# ============================================================================

BASE_DIR="${BASE_DIR:-~/iptv_sever}"
API_PORT="${API_PORT:-8088}"
API_HOST="${API_HOST:-0.0.0.0}"

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
# 检查函数
# ============================================================================

# 检查服务进程
check_process() {
    log_info "检查服务进程..."
    local pids=$(pgrep -f 'uvicorn.*api.main:app' 2>/dev/null || echo "")
    
    if [ -n "$pids" ]; then
        log_success "服务进程运行中 (PID: $pids)"
        # 显示进程详细信息
        ps aux | grep -E "uvicorn.*api.main:app" | grep -v grep || true
        return 0
    else
        log_warning "未找到服务进程"
        return 1
    fi
}

# 检查端口监听
check_port() {
    log_info "检查端口 $API_PORT 监听状态..."
    
    # 尝试使用 ss 命令
    if command -v ss >/dev/null 2>&1; then
        local port_info=$(ss -tlnp 2>/dev/null | grep ":$API_PORT " || echo "")
        if [ -n "$port_info" ]; then
            log_success "端口 $API_PORT 正在监听"
            echo "$port_info"
            return 0
        fi
    fi
    
    # 尝试使用 netstat 命令
    if command -v netstat >/dev/null 2>&1; then
        local port_info=$(netstat -tlnp 2>/dev/null | grep ":$API_PORT " || echo "")
        if [ -n "$port_info" ]; then
            log_success "端口 $API_PORT 正在监听"
            echo "$port_info"
            return 0
        fi
    fi
    
    # 尝试使用 lsof 命令
    if command -v lsof >/dev/null 2>&1; then
        local port_info=$(lsof -i :$API_PORT 2>/dev/null || echo "")
        if [ -n "$port_info" ]; then
            log_success "端口 $API_PORT 正在监听"
            echo "$port_info"
            return 0
        fi
    fi
    
    log_warning "端口 $API_PORT 未在监听"
    return 1
}

# 检查日志文件
check_logs() {
    local log_file="$BASE_DIR/api.log"
    
    log_info "检查日志文件: $log_file"
    
    if [ ! -f "$log_file" ]; then
        log_warning "日志文件不存在"
        return 1
    fi
    
    log_info "日志文件大小: $(du -h "$log_file" | cut -f1)"
    echo ""
    log_info "最近 30 行日志:"
    echo "----------------------------------------"
    tail -30 "$log_file" 2>/dev/null || echo "无法读取日志文件"
    echo "----------------------------------------"
}

# 测试本地连接
test_local_connection() {
    log_info "测试本地连接..."
    
    if command -v curl >/dev/null 2>&1; then
        log_info "使用 curl 测试 http://127.0.0.1:$API_PORT..."
        if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "http://127.0.0.1:$API_PORT" | grep -q "200\|404\|405"; then
            log_success "本地连接成功"
            return 0
        else
            log_warning "本地连接失败"
            return 1
        fi
    elif command -v wget >/dev/null 2>&1; then
        log_info "使用 wget 测试 http://127.0.0.1:$API_PORT..."
        if wget -q -O /dev/null --timeout=3 "http://127.0.0.1:$API_PORT" 2>/dev/null; then
            log_success "本地连接成功"
            return 0
        else
            log_warning "本地连接失败"
            return 1
        fi
    else
        log_warning "未找到 curl 或 wget，无法测试连接"
        return 1
    fi
}

# 检查防火墙
check_firewall() {
    log_info "检查防火墙状态..."
    
    # 检查 ufw (Ubuntu)
    if command -v ufw >/dev/null 2>&1; then
        local ufw_status=$(ufw status 2>/dev/null | head -1 || echo "")
        if echo "$ufw_status" | grep -qi "active"; then
            log_warning "UFW 防火墙已启用"
            log_info "UFW 状态:"
            ufw status | head -5
            echo ""
            log_info "如果需要开放端口，运行: sudo ufw allow $API_PORT/tcp"
        else
            log_info "UFW 防火墙未启用"
        fi
    fi
    
    # 检查 firewalld (CentOS/RHEL)
    if command -v firewall-cmd >/dev/null 2>&1; then
        if systemctl is-active --quiet firewalld 2>/dev/null; then
            log_warning "firewalld 防火墙已启用"
            log_info "如果需要开放端口，运行: sudo firewall-cmd --add-port=$API_PORT/tcp --permanent && sudo firewall-cmd --reload"
        else
            log_info "firewalld 防火墙未启用"
        fi
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    log_info "=========================================="
    log_info "服务状态检查"
    log_info "=========================================="
    echo ""
    
    log_info "配置信息:"
    log_info "  工作目录: $BASE_DIR"
    log_info "  监听地址: $API_HOST:$API_PORT"
    echo ""
    
    # 1. 检查进程
    local process_running=false
    if check_process; then
        process_running=true
    fi
    echo ""
    
    # 2. 检查端口
    local port_listening=false
    if check_port; then
        port_listening=true
    fi
    echo ""
    
    # 3. 检查日志
    check_logs
    echo ""
    
    # 4. 测试本地连接
    if [ "$process_running" = "true" ] && [ "$port_listening" = "true" ]; then
        test_local_connection
        echo ""
    fi
    
    # 5. 检查防火墙
    check_firewall
    echo ""
    
    # 总结
    log_info "=========================================="
    log_info "诊断总结"
    log_info "=========================================="
    
    if [ "$process_running" = "true" ] && [ "$port_listening" = "true" ]; then
        log_success "服务运行正常"
        log_info "如果无法从外部访问，请检查："
        log_info "  1. 防火墙设置（见上方）"
        log_info "  2. 服务器网络配置"
        log_info "  3. 路由器/网关端口转发"
    elif [ "$process_running" = "true" ] && [ "$port_listening" = "false" ]; then
        log_error "服务进程存在但端口未监听"
        log_info "可能原因："
        log_info "  1. 服务启动失败（查看日志）"
        log_info "  2. 端口被其他程序占用"
        log_info "  3. 服务绑定地址错误"
    elif [ "$process_running" = "false" ]; then
        log_error "服务未运行"
        log_info "请运行: bash $BASE_DIR/start.sh"
    fi
}

# 运行主函数
main "$@"
