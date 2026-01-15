#!/bin/bash
# -*- coding: utf-8 -*-
#
# 配置SSH密钥到路由器

set -e

SSH_KEY="/Users/yushuangyang/Documents/dev/iptv/.cursor_iptvhelper_ed25519"
PUB_KEY_FILE="/Users/yushuangyang/Documents/dev/iptv/.cursor_iptvhelper_ed25519.pub"
ROUTER="root@192.168.1.250"

# 颜色输出
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

echo "=========================================="
echo "配置SSH密钥到路由器"
echo "=========================================="
echo ""

# 检查密钥文件
if [ ! -f "$SSH_KEY" ] || [ ! -f "$PUB_KEY_FILE" ]; then
    echo -e "${RED}错误: SSH密钥文件不存在${NC}"
    echo "请先运行: ssh-keygen -t ed25519 -f .cursor_iptvhelper_ed25519 -N \"\""
    exit 1
fi

# 读取公钥
PUB_KEY=$(cat "$PUB_KEY_FILE")
echo "公钥内容："
echo "$PUB_KEY"
echo ""

# 方法1：尝试使用ssh-copy-id（如果支持）
echo "方法1: 尝试使用 ssh-copy-id..."
if command -v ssh-copy-id >/dev/null 2>&1; then
    if ssh-copy-id -i "$PUB_KEY_FILE" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$ROUTER" 2>&1; then
        echo -e "${GREEN}✓ 使用 ssh-copy-id 成功配置密钥${NC}"
    else
        echo -e "${YELLOW}ssh-copy-id 失败，尝试手动配置...${NC}"
        METHOD=2
    fi
else
    echo -e "${YELLOW}ssh-copy-id 不可用，使用手动配置...${NC}"
    METHOD=2
fi

# 方法2：手动配置（需要密码）
if [ "${METHOD:-}" = "2" ]; then
    echo ""
    echo "方法2: 手动配置（需要输入路由器密码）..."
    echo ""
    
    # 在路由器上创建.ssh目录并添加公钥
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$ROUTER" "
        mkdir -p ~/.ssh
        chmod 700 ~/.ssh
        echo '$PUB_KEY' >> ~/.ssh/authorized_keys
        chmod 600 ~/.ssh/authorized_keys
        echo 'SSH密钥已添加到路由器'
    " 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 手动配置成功${NC}"
    else
        echo -e "${RED}✗ 手动配置失败${NC}"
        echo ""
        echo "请手动执行以下步骤："
        echo "1. 登录路由器: ssh root@192.168.1.250"
        echo "2. 创建目录: mkdir -p ~/.ssh && chmod 700 ~/.ssh"
        echo "3. 添加公钥: echo '$PUB_KEY' >> ~/.ssh/authorized_keys"
        echo "4. 设置权限: chmod 600 ~/.ssh/authorized_keys"
        exit 1
    fi
fi

# 测试无密码登录
echo ""
echo "测试SSH连接..."
if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 "$ROUTER" "echo 'SSH密钥登录成功！' && uname -a" 2>&1; then
    echo -e "${GREEN}✓ SSH密钥配置成功！${NC}"
    echo ""
    echo "现在可以使用以下命令同步代码："
    echo "  ./sync_to_router.sh"
else
    echo -e "${YELLOW}⚠ SSH密钥测试失败，但可能已配置成功${NC}"
    echo "请手动测试: ssh -i $SSH_KEY $ROUTER"
fi

