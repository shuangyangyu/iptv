# Home Assistant 部署指南

## 问题说明

如果通过 Supervisor addon 安装遇到 SSL 错误（Git clone 失败），可以直接使用 docker-compose 部署，功能完全相同。

## 快速部署

### 方法 1：使用部署脚本（推荐）

```bash
# 在项目根目录执行
./deploy_to_ha.sh
```

脚本会自动：
1. 检查 SSH 连接
2. 同步项目文件到 HA 设备
3. 构建并启动 Docker 容器

### 方法 2：手动部署

#### 步骤 1：将代码复制到 HA 设备

```bash
# 使用 scp
scp -r /path/to/iptv root@192.168.1.249:/opt/iptv

# 或使用 rsync（推荐，更高效）
rsync -avz \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='node_modules' \
    --exclude='文档' \
    --exclude='iptv_sever/tests' \
    --exclude='scripts' \
    ./ root@192.168.1.249:/opt/iptv
```

#### 步骤 2：在 HA 设备上启动

```bash
# SSH 到 HA 设备
ssh root@192.168.1.249

# 进入项目目录
cd /opt/iptv

# 构建并启动
docker-compose build
docker-compose up -d

# 查看状态
docker-compose ps
```

#### 步骤 3：访问服务

当前 Docker Compose 部署由前端 nginx 统一对外监听 `8088`：

- **Web 控制台**: http://192.168.1.249:8088
- **API 文档**: http://192.168.1.249:8088/docs
- **健康检查**: http://192.168.1.249:8088/health
- **M3U 文件**: http://192.168.1.249:8088/out/iptv.m3u
- **EPG 文件**: http://192.168.1.249:8088/out/epg.xml

## 常用命令

### 查看日志

```bash
# SSH 到 HA 设备
ssh root@192.168.1.249
cd /opt/iptv

# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 重启服务

```bash
docker-compose restart
```

### 停止服务

```bash
docker-compose down
```

### 更新服务

```bash
# 1. 在本地更新代码并推送到 GitHub
git push

# 2. 在 HA 设备上拉取更新
cd /opt/iptv
git pull

# 3. 重新构建并启动
docker-compose build
docker-compose up -d
```

## 配置说明

### 网络接口配置

服务启动后，通过 Web 界面配置：

1. 访问：http://192.168.1.249:8088
2. 进入配置页面
3. 设置：
   - `source_iface`: 源网络接口（用于接收 IPTV 组播流）
   - `local_iface`: 本地网络接口（用于对外提供服务）

### 端口说明

- **8088**: Web 控制台、API 反向代理、`/out` 静态文件、回放代理。
- **8089**: FastAPI 后端服务端口，由 nginx 反代访问。
- **4022**: UDPXY 服务（UDP 转 HTTP 代理）。

## 与 Addon 的区别

使用 docker-compose 部署与 addon 部署功能完全相同：

| 特性 | docker-compose | Addon |
|------|----------------|-------|
| 功能 | 完全相同 | 完全相同 |
| 网络模式 | host 模式 | host 模式 |
| 数据持久化 | Docker volumes | /data 目录 |
| 管理方式 | docker-compose 命令 | Supervisor UI |
| 更新方式 | git pull + rebuild | Supervisor 更新 |

## 故障排查

### 1. 端口被占用

```bash
# 检查端口占用
lsof -i :8088
lsof -i :8089
lsof -i :4022

# 如果被占用，停止占用端口的服务
```

### 2. 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查容器状态
docker-compose ps
docker ps -a
```

### 3. 网络问题

确保 HA 设备能访问：
- 互联网（用于获取频道列表和 EPG）
- 本地网络（用于提供服务）

## 优势

使用 docker-compose 部署的优势：

1. 不需要解决 Supervisor Git clone 问题。
2. 部署链路更直接。
3. 更容易用 Docker 日志调试和维护。
4. 功能与 Addon 部署保持一致。
5. 可以随时通过代码同步和重新构建更新服务。

## 需要帮助？

如果遇到问题，请提供：
1. 错误信息
2. 日志输出
3. 网络配置信息
