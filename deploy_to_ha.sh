#!/bin/bash
# 部署脚本：将 IPTV 服务部署到 Home Assistant 设备

set -e

# 配置
HA_HOST="${HA_HOST:-192.168.1.249}"
HA_USER="${HA_USER:-root}"
# 如果 DEPLOY_PATH 以 ~ 开头，需要在远程服务器上展开
if [ -z "$DEPLOY_PATH" ]; then
    if [ "$HA_USER" = "root" ]; then
        DEPLOY_PATH="/opt/iptv"
    else
        DEPLOY_PATH="/home/${HA_USER}/iptv"
    fi
fi

echo "=========================================="
echo "IPTV 服务部署到 Home Assistant"
echo "=========================================="
echo ""
echo "目标设备: ${HA_USER}@${HA_HOST}"
echo "部署路径: ${DEPLOY_PATH}"
echo ""

# 检查 SSH 连接
echo "1. 检查 SSH 连接..."
if ! ssh -o ConnectTimeout=5 ${HA_USER}@${HA_HOST} "echo 'SSH 连接成功'" 2>/dev/null; then
    echo "❌ 无法连接到 HA 设备，请检查："
    echo "   - SSH 是否启用"
    echo "   - 主机地址是否正确: ${HA_HOST}"
    echo "   - 用户名是否正确: ${HA_USER}"
    exit 1
fi
echo "✅ SSH 连接成功"
echo ""

# 创建部署目录
echo "2. 创建部署目录..."
ssh ${HA_USER}@${HA_HOST} "mkdir -p ${DEPLOY_PATH}"
echo "✅ 目录创建成功"
echo ""

# 同步文件（排除不需要的文件）
echo "3. 同步项目文件..."
rsync -avz --progress \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='文档' \
    --exclude='iptv_sever/tests' \
    --exclude='scripts' \
    --exclude='.dockerignore' \
    --exclude='.gitignore' \
    --exclude='.syncignore' \
    ./ ${HA_USER}@${HA_HOST}:${DEPLOY_PATH}/

echo "✅ 文件同步完成"
echo ""

# 在远程设备上构建和启动
echo "4. 构建并启动服务..."
ssh ${HA_USER}@${HA_HOST} <<EOF
cd ${DEPLOY_PATH}

# 停止旧容器（如果存在）
docker-compose down 2>/dev/null || true

# 构建镜像
echo "构建 Docker 镜像..."
docker-compose build

# 启动服务
echo "启动服务..."
docker-compose up -d

# 等待服务启动
sleep 5

# 检查服务状态
docker-compose ps
EOF

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  - 前端界面: http://${HA_HOST}"
echo "  - 后端 API: http://${HA_HOST}:8088"
echo "  - API 文档: http://${HA_HOST}:8088/docs"
echo ""
echo "查看日志："
echo "  ssh ${HA_USER}@${HA_HOST} 'cd ${DEPLOY_PATH} && docker-compose logs -f'"
echo ""
echo "停止服务："
echo "  ssh ${HA_USER}@${HA_HOST} 'cd ${DEPLOY_PATH} && docker-compose down'"
echo ""
