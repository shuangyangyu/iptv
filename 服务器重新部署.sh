#!/bin/bash
# 在服务器上重新构建和部署 IPTV 服务

set -e

echo "=========================================="
echo "IPTV 服务重新部署"
echo "=========================================="
echo ""

# 检查是否在项目目录
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 停止现有服务
echo "1. 停止现有服务..."
docker-compose down || true
echo "✅ 服务已停止"
echo ""

# 清理旧镜像（可选）
read -p "是否清理旧镜像？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "2. 清理旧镜像..."
    docker-compose rm -f backend frontend || true
    docker rmi iptv-backend iptv-frontend 2>/dev/null || true
    echo "✅ 旧镜像已清理"
    echo ""
fi

# 拉取最新代码（如果使用 Git）
if [ -d ".git" ]; then
    echo "3. 拉取最新代码..."
    git pull origin master || echo "⚠️  Git 拉取失败，继续使用当前代码"
    echo ""
fi

# 重新构建镜像
echo "4. 重新构建镜像..."
docker-compose build --no-cache backend frontend
if [ $? -eq 0 ]; then
    echo "✅ 镜像构建成功"
else
    echo "❌ 镜像构建失败"
    exit 1
fi
echo ""

# 启动服务
echo "5. 启动服务..."
docker-compose up -d
if [ $? -eq 0 ]; then
    echo "✅ 服务启动成功"
else
    echo "❌ 服务启动失败"
    exit 1
fi
echo ""

# 等待服务就绪
echo "6. 等待服务就绪..."
sleep 5

# 检查服务状态
echo "7. 检查服务状态..."
docker-compose ps
echo ""

# 检查健康状态
echo "8. 检查健康状态..."
for i in {1..10}; do
    if curl -f http://localhost:8088/health > /dev/null 2>&1; then
        echo "✅ 后端服务健康检查通过"
        break
    else
        echo "⏳ 等待服务启动... ($i/10)"
        sleep 2
    fi
done
echo ""

# 显示日志
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - 前端: http://$(hostname -I | awk '{print $1}')"
echo "  - 后端 API: http://$(hostname -I | awk '{print $1}'):8088"
echo "  - API 文档: http://$(hostname -I | awk '{print $1}'):8088/docs"
echo ""
echo "查看日志:"
echo "  docker-compose logs -f backend"
echo ""
echo "查看容器状态:"
echo "  docker-compose ps"
echo ""
