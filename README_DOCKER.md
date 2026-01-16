# Docker 快速部署指南

## ✅ 现在可以在任何环境中使用 docker-compose 安装！

本项目已完全容器化，支持一键部署。

## 🚀 快速开始（使用 Docker Hub 镜像）

镜像已自动构建并推送到 Docker Hub，可以直接使用：

```bash
# 使用 Docker Hub 镜像（推荐）
# 详细说明请查看 README_DOCKERHUB.md
docker-compose pull
docker-compose up -d
```

**Docker Hub 镜像**:
- `shuangyangyu/iptv-backend:latest`
- `shuangyangyu/iptv-frontend:latest`

📖 详细使用说明请参考：[README_DOCKERHUB.md](README_DOCKERHUB.md)

---

## 🔨 从源码构建

如果想要从源码构建镜像，继续阅读本文档。

## 前置要求

1. **Docker** (版本 20.10+)
2. **Docker Compose** (版本 2.0+)

### 安装 Docker

**Linux:**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt-get install docker-compose-plugin
```

**macOS/Windows:**
- 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd iptv
```

### 2. 构建并启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps
```

### 3. 访问服务

- **前端界面**: http://localhost
- **后端 API**: http://localhost:8088
- **API 文档**: http://localhost:8088/docs

## 配置说明

### 网络模式

默认使用 `host` 网络模式，适合双网卡场景：
- 容器可以直接访问主机网络接口
- 支持多网卡配置（source_iface 和 local_iface）

### 数据持久化

数据自动保存在 Docker volumes 中：
- `iptv_out_data`: M3U/EPG 文件和 logos
- `iptv_state_data`: 配置和状态文件

### 端口说明

- **80**: 前端 Web 界面
- **8088**: 后端 API
- **4022**: UDPXY 服务（UDP 转 HTTP 代理）

## 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 更新代码后重新构建
docker-compose build --no-cache
docker-compose up -d
```

## 故障排查

### 1. 端口被占用

```bash
# 检查端口占用
lsof -i :80
lsof -i :8088
lsof -i :4022

# 如果被占用，停止占用端口的服务或修改 docker-compose.yml
```

### 2. 构建失败

```bash
# 查看详细构建日志
docker-compose build --progress=plain

# 清理并重新构建
docker-compose down -v
docker-compose build --no-cache
```

### 3. 容器无法启动

```bash
# 查看容器日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器状态
docker-compose ps
docker ps -a
```

### 4. UDPXY 未运行

```bash
# 进入容器检查
docker-compose exec backend bash
which udpxy
udpxy -h

# 查看日志
docker-compose logs backend | grep udpxy
```

## 环境要求

- **操作系统**: 
  - ✅ Linux (推荐，支持 host 网络模式)
  - ✅ macOS (使用 bridge 网络模式)
  - ✅ Windows (WSL2，使用 bridge 网络模式)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **内存**: 至少 2GB
- **磁盘**: 至少 5GB 可用空间

## 网络模式说明

### Linux 环境（推荐使用 host 模式）

默认配置使用 `host` 网络模式，适合双网卡场景：
- 容器直接访问主机网络接口
- 支持多网卡配置
- 性能更好

### macOS/Windows 环境（使用 bridge 模式）

macOS 和 Windows 不支持 host 网络模式，需要修改配置：

1. 复制 bridge 网络配置：
```bash
cp docker-compose.bridge.yml.example docker-compose.override.yml
```

2. 修改 `nginx.conf`，将 `localhost:8088` 改为 `backend:8088`

3. 启动服务：
```bash
docker-compose up -d
```

## 生产环境建议

1. **使用非 root 用户运行容器**（在 Dockerfile 中添加）
2. **配置 HTTPS**（使用 nginx 反向代理 + SSL 证书）
3. **限制资源使用**（在 docker-compose.yml 中添加 limits）
4. **配置日志轮转**
5. **定期备份 volumes**

## 更多信息

详细文档请查看 [DOCKER.md](./DOCKER.md)
