#!/bin/bash
# Docker 构建和测试脚本

set -e

echo "=========================================="
echo "Docker 构建和测试"
echo "=========================================="
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker daemon 未运行，请先启动 Docker Desktop"
    exit 1
fi

echo "✅ Docker daemon 正在运行"
echo ""

# 清理旧的容器和镜像（可选）
read -p "是否清理旧的容器和镜像？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "清理旧的容器和镜像..."
    docker-compose down -v 2>/dev/null || true
    docker rmi iptv-backend iptv-frontend 2>/dev/null || true
    echo "✅ 清理完成"
    echo ""
fi

# 构建镜像
echo "开始构建 Docker 镜像..."
echo ""

echo "1. 构建后端镜像..."
docker-compose build backend
if [ $? -eq 0 ]; then
    echo "✅ 后端镜像构建成功"
else
    echo "❌ 后端镜像构建失败"
    exit 1
fi
echo ""

echo "2. 构建前端镜像..."
docker-compose build frontend
if [ $? -eq 0 ]; then
    echo "✅ 前端镜像构建成功"
else
    echo "❌ 前端镜像构建失败"
    exit 1
fi
echo ""

# 检查镜像
echo "3. 检查镜像..."
docker images | grep -E "iptv|REPOSITORY" || true
echo ""

# 启动服务
echo "4. 启动服务..."
docker-compose up -d
if [ $? -eq 0 ]; then
    echo "✅ 服务启动成功"
else
    echo "❌ 服务启动失败"
    exit 1
fi
echo ""

# 等待服务就绪
echo "5. 等待服务就绪..."
sleep 5

# 检查服务状态
echo "6. 检查服务状态..."
docker-compose ps
echo ""

# 检查健康状态
echo "7. 检查健康状态..."
echo "后端健康检查:"
curl -f http://localhost:8088/health 2>/dev/null && echo "✅ 后端服务正常" || echo "❌ 后端服务异常"
echo ""

echo "前端健康检查:"
curl -f http://localhost/health 2>/dev/null && echo "✅ 前端服务正常" || echo "❌ 前端服务异常"
echo ""

# 显示日志
echo "8. 显示服务日志（最后 20 行）..."
echo "后端日志:"
docker-compose logs --tail=20 backend
echo ""
echo "前端日志:"
docker-compose logs --tail=20 frontend
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - 前端: http://localhost"
echo "  - 后端 API: http://localhost:8088"
echo "  - API 文档: http://localhost:8088/docs"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo ""
