# Docker Hub 镜像使用指南

本项目的 Docker 镜像已自动构建并推送到 Docker Hub。

## 镜像列表

- **Backend**: `shuangyangyu/iptv-backend:latest`
- **Frontend**: `shuangyangyu/iptv-frontend:latest`

## 快速开始

### 方法一：直接使用 Docker Hub 镜像（推荐）

#### 1. 创建 docker-compose.yml

```yaml
services:
  backend:
    image: shuangyangyu/iptv-backend:latest
    container_name: iptv-backend
    network_mode: host
    volumes:
      - iptv_out_data:/app/iptv_sever/out
      - iptv_state_data:/app/iptv_sever/api
    environment:
      - API_PORT=8088
      - API_HOST=0.0.0.0
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    image: shuangyangyu/iptv-frontend:latest
    container_name: iptv-frontend
    network_mode: host
    depends_on:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  iptv_out_data:
    driver: local
  iptv_state_data:
    driver: local
```

#### 2. 启动服务

```bash
# 拉取并启动
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 3. 访问服务

- **前端界面**: http://localhost
- **后端 API**: http://localhost:8088
- **API 文档**: http://localhost:8088/docs

### 方法二：手动拉取镜像

```bash
# 拉取镜像
docker pull shuangyangyu/iptv-backend:latest
docker pull shuangyangyu/iptv-frontend:latest

# 运行 backend
docker run -d \
  --name iptv-backend \
  --network host \
  -v iptv_out_data:/app/iptv_sever/out \
  -v iptv_state_data:/app/iptv_sever/api \
  -e API_PORT=8088 \
  -e API_HOST=0.0.0.0 \
  --restart unless-stopped \
  shuangyangyu/iptv-backend:latest

# 运行 frontend
docker run -d \
  --name iptv-frontend \
  --network host \
  --restart unless-stopped \
  shuangyangyu/iptv-frontend:latest
```

## 镜像自动更新

### GitHub Actions 自动构建

每次推送到 `master` 分支时，GitHub Actions 会自动：
1. 构建 backend 和 frontend 镜像
2. 推送到 Docker Hub
3. 更新 `latest` 标签

### 更新镜像

```bash
# 拉取最新镜像
docker-compose pull

# 重启服务使用新镜像
docker-compose up -d
```

## 镜像说明

### iptv-backend:latest

**基础镜像**: `python:3.11-slim`

**包含内容**:
- FastAPI 后端服务
- UDPXY（UDP 转 HTTP 代理）
- Cron 定时任务服务
- 完整的 Python 依赖

**端口**:
- `8088`: FastAPI API 端口
- `4022`: UDPXY 服务端口

**环境变量**:
- `API_PORT`: API 端口（默认: 8088）
- `API_HOST`: 绑定地址（默认: 0.0.0.0）

### iptv-frontend:latest

**基础镜像**: `nginx:alpine`

**包含内容**:
- Vue.js 前端静态文件
- Nginx Web 服务器
- 反向代理配置

**端口**:
- `80`: HTTP Web 服务

## 配置说明

### 网络模式

默认使用 `host` 网络模式（Linux 推荐）：
- 容器可以直接访问主机网络接口
- 支持多网卡配置（source_iface 和 local_iface）
- 性能更好

### macOS/Windows 环境

macOS 和 Windows 不支持 `host` 网络模式，需要修改配置：

1. 修改 `docker-compose.yml`，使用 bridge 网络：

```yaml
services:
  backend:
    image: shuangyangyu/iptv-backend:latest
    ports:
      - "8088:8088"
      - "4022:4022"
    # ... 其他配置

  frontend:
    image: shuangyangyu/iptv-frontend:latest
    ports:
      - "80:80"
    # ... 其他配置
```

2. 修改 nginx 配置（在容器内）：
   - 将 `localhost:8088` 改为 `backend:8088`

### 数据持久化

数据自动保存在 Docker volumes 中：
- `iptv_out_data`: M3U/EPG 文件和 logos
- `iptv_state_data`: 配置和状态文件

备份 volumes：
```bash
docker run --rm \
  -v iptv_out_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/iptv_out_data_backup.tar.gz /data
```

## 常用命令

```bash
# 拉取最新镜像
docker-compose pull

# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启服务
docker-compose restart

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh

# 更新并重启
docker-compose pull && docker-compose up -d
```

## 故障排查

### 1. 镜像拉取失败

```bash
# 检查网络连接
ping hub.docker.com

# 手动拉取镜像
docker pull shuangyangyu/iptv-backend:latest
docker pull shuangyangyu/iptv-frontend:latest
```

### 2. 容器启动失败

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器状态
docker-compose ps
docker ps -a

# 检查端口占用
lsof -i :80
lsof -i :8088
lsof -i :4022
```

### 3. 服务无法访问

```bash
# 检查容器网络
docker network ls
docker network inspect bridge

# 检查容器内部服务
docker-compose exec backend curl http://localhost:8088/health
docker-compose exec frontend wget -O- http://localhost/health
```

## 版本标签

当前可用标签：
- `latest`: 最新版本（自动更新）

## 镜像大小

- `iptv-backend:latest`: 约 500MB（包含 udpxy 编译工具）
- `iptv-frontend:latest`: 约 20MB（Alpine 基础镜像）

## 源码构建

如果您想从源码构建镜像：

```bash
# 克隆仓库
git clone https://github.com/shuangyangyu/iptv.git
cd iptv

# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

详细构建说明请参考 [README_DOCKER.md](README_DOCKER.md)

## 相关链接

- **GitHub 仓库**: https://github.com/shuangyangyu/iptv
- **Docker Hub Backend**: https://hub.docker.com/r/shuangyangyu/iptv-backend
- **Docker Hub Frontend**: https://hub.docker.com/r/shuangyangyu/iptv-frontend
- **项目文档**: [README_DOCKER.md](README_DOCKER.md)

## 支持

如遇问题，请：
1. 查看 [故障排查](#故障排查) 部分
2. 查看 GitHub Issues: https://github.com/shuangyangyu/iptv/issues
3. 查看项目文档: [文档目录](文档/)
