#!/bin/bash
# -*- coding: utf-8 -*-
#
# 部署配置文件
# 统一管理 SSH、服务器等配置信息

# 项目根目录（脚本所在目录的父目录）
# 优先使用 BASH_SOURCE[0]（直接执行时），否则使用 $0
if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    # 通过 source 加载时，BASH_SOURCE[0] 指向 config.sh
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    # 直接执行时，使用 $0
    SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
fi
# 如果 SCRIPT_DIR 不是 scripts 目录，尝试查找
if [ "$(basename "$SCRIPT_DIR")" != "scripts" ]; then
    # 尝试从当前目录向上查找 scripts 目录
    current_dir="$SCRIPT_DIR"
    while [ "$current_dir" != "/" ]; do
        if [ -d "$current_dir/scripts" ] && [ -f "$current_dir/scripts/config.sh" ]; then
            SCRIPT_DIR="$(cd "$current_dir/scripts" && pwd)"
            break
        fi
        current_dir="$(dirname "$current_dir")"
    done
fi
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# SSH 配置
# 优先使用 .ssh_router/router_key，如果不存在则使用旧的密钥
if [ -f "$PROJECT_ROOT/.ssh_router/router_key" ]; then
    SSH_KEY="$PROJECT_ROOT/.ssh_router/router_key"
elif [ -f "$PROJECT_ROOT/.cursor_iptvhelper_ed25519" ]; then
    SSH_KEY="$PROJECT_ROOT/.cursor_iptvhelper_ed25519"
else
    # 如果都不存在，尝试使用当前目录下的密钥
    if [ -f ".cursor_iptvhelper_ed25519" ]; then
        SSH_KEY="$(pwd)/.cursor_iptvhelper_ed25519"
    else
        SSH_KEY="$PROJECT_ROOT/.ssh_router/router_key"  # 默认路径（可能不存在）
        log_warning "未找到 SSH 密钥文件，请运行 ./scripts/setup_ssh.sh 配置 SSH"
    fi
fi
SSH_USER="shuangyang"
SSH_HOST="192.168.1.241"
SSH_TARGET="$SSH_USER@$SSH_HOST"

# 服务器路径配置
# 注意：使用 ~ 符号，在远程执行时会自动展开为用户主目录
SERVER_BASE_DIR="~/iptv_sever"
SERVER_API_DIR="$SERVER_BASE_DIR/api"
SERVER_BACKEND_DIR="$SERVER_BASE_DIR/backend"
SERVER_FRONTEND_DIR="$SERVER_BASE_DIR/frontend"
SERVER_TESTS_DIR="$SERVER_BASE_DIR/tests"
SERVER_OUT_DIR="$SERVER_BASE_DIR/out"
SERVER_VENV_DIR="$SERVER_BASE_DIR/venv"

# 本地路径配置
LOCAL_BASE_DIR="$PROJECT_ROOT/iptv_sever"
LOCAL_API_DIR="$LOCAL_BASE_DIR/api"
LOCAL_BACKEND_DIR="$LOCAL_BASE_DIR/backend"
LOCAL_FRONTEND_DIR="$LOCAL_BASE_DIR/frontend"
LOCAL_TESTS_DIR="$LOCAL_BASE_DIR/tests"

# 服务配置
API_PORT=8088
API_HOST="0.0.0.0"

# Python 配置
PYTHON_CMD="python3"
VENV_ACTIVATE="$SERVER_VENV_DIR/bin/activate"

# 日志文件
LOG_FILE="$SERVER_BASE_DIR/deploy.log"

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

# 输出函数
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

# 检查 SSH 连接
check_ssh() {
    if [ ! -f "$SSH_KEY" ]; then
        log_error "SSH 密钥文件不存在: $SSH_KEY"
        log_info "请检查以下路径："
        log_info "  - $PROJECT_ROOT/.ssh_router/router_key"
        log_info "  - $PROJECT_ROOT/.cursor_iptvhelper_ed25519"
        log_info "或运行: ./scripts/setup_ssh.sh"
        return 1
    fi
    
    ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        -o ConnectTimeout=5 \
        "$SSH_TARGET" "echo 'SSH连接成功'" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        return 0
    else
        log_error "SSH 连接失败，请检查配置"
        return 1
    fi
}

# 执行远程命令（带超时）
remote_exec() {
    ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        -o ConnectTimeout=10 \
        -o ServerAliveInterval=5 \
        -o ServerAliveCountMax=2 \
        "$SSH_TARGET" "$1" 2>&1
}
