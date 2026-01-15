#!/bin/bash
# 配置 SSH 密钥到服务器，实现免密登录

set -e

echo "=========================================="
echo "SSH 密钥配置工具"
echo "=========================================="
echo ""

# 检查 SSH 密钥是否存在
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo "❌ 未找到 SSH 公钥"
    echo ""
    echo "正在生成 SSH 密钥..."
    ssh-keygen -t rsa -b 4096 -C "$(whoami)@$(hostname)"
    echo ""
fi

# 显示公钥
echo "你的 SSH 公钥："
echo "----------------------------------------"
cat ~/.ssh/id_rsa.pub
echo "----------------------------------------"
echo ""

# 获取服务器信息
read -p "请输入服务器 IP 地址 (默认: 192.168.1.249): " SERVER_IP
SERVER_IP=${SERVER_IP:-192.168.1.249}

read -p "请输入 SSH 用户名 (默认: root): " SERVER_USER
SERVER_USER=${SERVER_USER:-root}

read -p "请输入 SSH 端口 (默认: 22): " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-22}

echo ""
echo "目标服务器: ${SERVER_USER}@${SERVER_IP}:${SERVER_PORT}"
echo ""

# 测试连接
echo "1. 测试 SSH 连接..."
if ssh -o ConnectTimeout=5 -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} "echo '连接成功'" 2>/dev/null; then
    echo "✅ SSH 连接成功"
else
    echo "❌ SSH 连接失败"
    echo "请检查："
    echo "  - 服务器 IP 是否正确: ${SERVER_IP}"
    echo "  - 用户名是否正确: ${SERVER_USER}"
    echo "  - 端口是否正确: ${SERVER_PORT}"
    echo "  - 服务器是否开启了 SSH 服务"
    exit 1
fi
echo ""

# 复制公钥到服务器
echo "2. 复制 SSH 公钥到服务器..."
echo "（可能需要输入一次密码）"

# 方法 1：使用 ssh-copy-id（推荐）
if command -v ssh-copy-id > /dev/null; then
    ssh-copy-id -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP}
else
    # 方法 2：手动复制
    cat ~/.ssh/id_rsa.pub | ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} \
        "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
fi

if [ $? -eq 0 ]; then
    echo "✅ SSH 公钥已复制到服务器"
else
    echo "❌ 复制失败"
    exit 1
fi
echo ""

# 测试免密登录
echo "3. 测试免密登录..."
if ssh -o ConnectTimeout=5 -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} "echo '免密登录成功'" 2>/dev/null; then
    echo "✅ 免密登录配置成功！"
else
    echo "⚠️  免密登录可能还未生效，请稍后再试"
    echo "   如果仍然需要密码，请检查服务器上的 ~/.ssh/authorized_keys 文件权限"
fi
echo ""

# 创建 SSH 配置文件（可选）
read -p "是否创建 SSH 配置文件以便快速连接？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SSH_CONFIG="$HOME/.ssh/config"
    CONFIG_ENTRY="iptv-server"
    
    # 检查是否已存在
    if grep -q "Host ${CONFIG_ENTRY}" ${SSH_CONFIG} 2>/dev/null; then
        echo "⚠️  SSH 配置文件中已存在 ${CONFIG_ENTRY}"
        read -p "是否覆盖？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # 删除旧配置
            sed -i.bak "/^Host ${CONFIG_ENTRY}/,/^$/d" ${SSH_CONFIG} 2>/dev/null || true
        else
            echo "跳过配置"
            exit 0
        fi
    fi
    
    # 添加新配置
    cat >> ${SSH_CONFIG} <<EOF

Host ${CONFIG_ENTRY}
    HostName ${SERVER_IP}
    User ${SERVER_USER}
    Port ${SERVER_PORT}
    IdentityFile ~/.ssh/id_rsa
EOF
    
    chmod 600 ${SSH_CONFIG}
    echo "✅ SSH 配置文件已创建"
    echo ""
    echo "现在可以使用以下命令快速连接："
    echo "  ssh ${CONFIG_ENTRY}"
fi

echo ""
echo "=========================================="
echo "✅ SSH 密钥配置完成！"
echo "=========================================="
echo ""
echo "现在可以使用以下方式连接："
echo "  ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP}"
if [ -f ${SSH_CONFIG} ] && grep -q "Host ${CONFIG_ENTRY}" ${SSH_CONFIG} 2>/dev/null; then
    echo "  或: ssh ${CONFIG_ENTRY}"
fi
echo ""
