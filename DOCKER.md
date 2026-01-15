# Docker 部署指南

## 概述

本项目已支持 Docker 容器化部署，包含以下组件：

- **后端容器**：FastAPI 服务（端口 8088）+ udpxy 服务（端口 4022）
- **前端容器**：nginx 静态服务（端口 80）

## 前置要求

1. 安装 Docker 和 Docker Compose
   - Docker Desktop: https://www.docker.com/products/docker-desktop
   - 或 Linux: `apt-get install docker.io docker-compose`

2. 确保 Docker daemon 正在运行
   ```bash
   docker info
   ```

## 快速开始

### 1. 构建镜像

```bash
# 构建所有镜像
docker-compose build

# 或使用测试脚本（推荐）
./docker-test.sh
```

### 2. 启动服务

```bash
docker-compose up -d
```

### 3. 查看服务状态

```bash
docker-compose ps
```

### 4. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5. 停止服务

```bash
docker-compose down
```

## 访问服务

- **前端界面**: http://localhost
- **后端 API**: http://localhost:8088
- **API 文档**: http://localhost:8088/docs
- **健康检查**: http://localhost:8088/health

## 网络配置

### 双网卡场景

项目使用 `network_mode: host` 以支持双网卡场景：

- **source_iface**: 用于接收 IPTV 组播流
- **local_iface**: 用于对外提供服务

容器启动后，通过 Web 界面或 API 配置网卡名称：
- 访问 http://localhost 进入配置页面
- 或使用 API: `POST /api/v1/config`

### 修改网络模式

如果需要使用 bridge 网络（更安全但配置复杂），修改 `docker-compose.yml`:

```yaml
backend:
  # 注释掉 network_mode: host
  # network_mode: host
  networks:
    - iptv-network
  cap_add:
    - NET_RAW
    - NET_ADMIN

frontend:
  # 注释掉 network_mode: host
  # network_mode: host
  ports:
    - "80:80"
  networks:
    - iptv-network

networks:
  iptv-network:
    driver: bridge
```

同时修改 `nginx.conf` 中的 `localhost:8088` 为 `backend:8088`。

## 数据持久化

数据存储在 Docker volumes 中：

- `iptv_out_data`: M3U/EPG 文件和 logos
- `iptv_state_data`: 状态文件和日志

查看 volumes:
```bash
docker volume ls | grep iptv
```

备份数据:
```bash
docker run --rm -v iptv_out_data:/data -v $(pwd):/backup alpine tar czf /backup/iptv_out_backup.tar.gz -C /data .
```

恢复数据:
```bash
docker run --rm -v iptv_out_data:/data -v $(pwd):/backup alpine tar xzf /backup/iptv_out_backup.tar.gz -C /data
```

## 环境变量

后端容器支持以下环境变量：

- `API_PORT`: API 端口（默认 8088）
- `API_HOST`: 监听地址（默认 0.0.0.0）

## 故障排查

### 1. 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器状态
docker-compose ps
```

### 2. udpxy 未安装

如果构建时 udpxy 安装失败，检查构建日志：
```bash
docker-compose build backend 2>&1 | grep -i udpxy
```

### 3. 端口被占用

```bash
# 检查端口占用
lsof -i :8088
lsof -i :80
lsof -i :4022

# 修改 docker-compose.yml 中的端口映射
```

### 4. 网络问题

如果使用 host 网络模式，确保：
- 主机网络正常
- 网卡配置正确
- 防火墙规则允许访问

## 开发模式

### 挂载代码目录（热重载）

修改 `docker-compose.yml`，添加 volumes:

```yaml
backend:
  volumes:
    - ./iptv_sever:/app/iptv_sever
    - iptv_out_data:/app/iptv_sever/out
    - iptv_state_data:/app/iptv_sever/api
```

### 调试模式

进入容器调试：
```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh
```

## 生产部署建议

1. **使用非 root 用户运行**（在 Dockerfile 中添加）
2. **配置 HTTPS**（使用 nginx 反向代理 + SSL 证书）
3. **限制资源使用**（在 docker-compose.yml 中添加 limits）
4. **配置日志轮转**
5. **定期备份 volumes**

## 测试

运行测试脚本：
```bash
./docker-test.sh
```

测试脚本会：
1. 检查 Docker 环境
2. 构建镜像
3. 启动服务
4. 检查健康状态
5. 显示日志

## 常见问题

### Q: udpxy 安装失败怎么办？

A: 检查网络连接，或使用预编译的 udpxy 二进制文件（修改 Dockerfile.backend）

### Q: 如何修改端口？

A: 修改 `docker-compose.yml` 中的端口映射和环境变量

### Q: 数据在哪里？

A: 数据在 Docker volumes 中，使用 `docker volume inspect` 查看位置

### Q: 如何更新代码？

A: 重新构建镜像：`docker-compose build && docker-compose up -d`

## 相关文件

- `Dockerfile.backend`: 后端镜像定义
- `Dockerfile.frontend`: 前端镜像定义
- `docker-compose.yml`: 容器编排配置
- `nginx.conf`: nginx 配置
- `.dockerignore`: Docker 构建忽略文件
- `docker-test.sh`: 测试脚本
