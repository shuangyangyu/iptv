#!/bin/bash
# -*- coding: utf-8 -*-
#
# 修复OpenWrt SSH密钥配置

set -e

SSH_KEY="/Users/yushuangyang/Documents/dev/iptv/.cursor_iptvhelper_ed25519"
PUB_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINgJzCmJoNqy90q0+8ov2Yzo+LNnxOAKh/xu5LlPbtLk iptv_helper_key"
ROUTER="root@192.168.1.250"

echo "=========================================="
echo "修复OpenWrt SSH密钥配置"
echo "=========================================="
echo ""

echo "正在配置OpenWrt SSH密钥..."
echo "（需要输入路由器密码）"
echo ""

# 配置标准SSH路径
ssh "$ROUTER" "
    # 确保.ssh目录存在
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # 添加公钥（如果不存在）
    if ! grep -q 'iptv_helper_key' ~/.ssh/authorized_keys 2>/dev/null; then
        echo '$PUB_KEY' >> ~/.ssh/authorized_keys
        echo '已添加到 ~/.ssh/authorized_keys'
    else
        echo '公钥已存在于 ~/.ssh/authorized_keys'
    fi
    chmod 600 ~/.ssh/authorized_keys
    
    # 配置dropbear（OpenWrt常用）
    if [ -d /etc/dropbear ]; then
        if ! grep -q 'iptv_helper_key' /etc/dropbear/authorized_keys 2>/dev/null; then
            echo '$PUB_KEY' >> /etc/dropbear/authorized_keys
            echo '已添加到 /etc/dropbear/authorized_keys'
        else
            echo '公钥已存在于 /etc/dropbear/authorized_keys'
        fi
    fi
    
    echo ''
    echo '配置完成！'
    echo '标准SSH路径: ~/.ssh/authorized_keys'
    echo 'Dropbear路径: /etc/dropbear/authorized_keys（如果存在）'
"

echo ""
echo "测试SSH连接..."
if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 "$ROUTER" "echo 'SSH密钥连接成功！' && uname -a" 2>&1; then
    echo "✅ SSH密钥配置成功！"
else
    echo "⚠️  连接测试失败，但配置可能已成功"
    echo "请手动测试: ssh -i $SSH_KEY $ROUTER"
fi

