# IPTV Server Home Assistant Addon

IPTV M3U/EPG 生成服务的 Home Assistant addon，支持组播转 HTTP 代理（UDPXY）。

## 功能特性

- **M3U 播放列表生成**：从频道列表源自动生成 M3U 播放列表
- **EPG 电子节目单**：自动生成 XMLTV 格式的电子节目单
- **UDPXY 集成**：内置 UDPXY 服务，支持组播转 HTTP 代理
- **双网卡支持**：支持配置源网络接口和本地网络接口
- **自动更新**：支持定时任务自动更新 M3U 和 EPG
- **RESTful API**：提供完整的 REST API 接口

## 安装

### 方法 1：通过 GitHub 仓库安装

1. 在 Home Assistant 中，进入 **Supervisor** → **Add-on Store**
2. 点击右上角的 **⋮** 菜单，选择 **Repositories**
3. 添加仓库：`https://github.com/shuangyangyu/iptv`
4. 在 **Add-on Store** 中找到 **IPTV Server**，点击 **Install**

### 方法 2：手动安装

1. 将 addon 目录复制到 Home Assistant 的 addon 目录
2. 在 Supervisor 中刷新 addon 列表
3. 找到 **IPTV Server** 并安装

## 配置

### 基本配置

在 addon 配置页面可以设置以下选项：

- **api_port** (int, 默认: 8088): FastAPI 后端 API 端口
- **udpxy_port** (int, 默认: 4022): UDPXY UDP 转 HTTP 代理端口
- **source_iface** (str, 可选): 源网络接口名称（用于接收 IPTV 组播流）
- **local_iface** (str, 可选): 本地网络接口名称（用于对外提供服务）
- **log_level** (str, 默认: "info"): 日志级别（info/debug/warning/error）

### 配置示例

```yaml
api_port: 8088
udpxy_port: 4022
source_iface: eth1
local_iface: eth0
log_level: info
```

### 网络接口配置

如果使用双网卡场景：

- **source_iface**: 用于接收 IPTV 组播流的网络接口（通常是连接到 IPTV 网络的网卡）
- **local_iface**: 用于对外提供 Web 服务的网络接口（通常是连接到本地网络的网卡）

如果不配置网络接口，系统会尝试自动检测。

## 使用

### 启动 Addon

1. 在 Supervisor 中打开 **IPTV Server** addon
2. 配置选项（如需要）
3. 点击 **Start** 启动服务

### 访问服务

启动后，可以通过以下方式访问：

- **API 文档**: `http://<home-assistant-ip>:8088/docs`
- **健康检查**: `http://<home-assistant-ip>:8088/health`
- **M3U 文件**: `http://<home-assistant-ip>:8088/out/iptv.m3u`
- **EPG 文件**: `http://<home-assistant-ip>:8088/out/epg.xml`

### API 端点

主要 API 端点：

- `GET /api/v1/status` - 获取服务状态
- `GET /api/v1/config` - 获取配置
- `PUT /api/v1/config` - 更新配置
- `GET /api/v1/interfaces` - 获取网络接口列表
- `POST /api/v1/jobs/build` - 手动触发构建任务
- `GET /api/v1/udpxy/status` - 获取 UDPXY 状态
- `POST /api/v1/udpxy/start` - 启动 UDPXY
- `POST /api/v1/udpxy/stop` - 停止 UDPXY

完整 API 文档请访问 `/docs` 端点。

## 数据持久化

Addon 的数据存储在 `/data` 目录中：

- `state.json` - 配置和状态文件
- `out/` - M3U/EPG 文件和 logos
- `api.log` - 应用日志
- `udpxy.log` - UDPXY 日志（如果启用）

这些数据在 addon 更新或重启后会自动保留。

## 故障排查

### Addon 无法启动

1. 检查日志：在 Supervisor 中查看 addon 日志
2. 检查端口占用：确保 8088 和 4022 端口未被占用
3. 检查网络配置：确保网络接口配置正确

### UDPXY 无法启动

1. 检查网络接口：确保 `source_iface` 配置正确
2. 检查权限：确保 addon 有 `NET_ADMIN` 和 `NET_RAW` 权限
3. 查看日志：检查 `udpxy.log` 文件

### API 无法访问

1. 检查端口：确认 API 端口（默认 8088）可访问
2. 检查防火墙：确保防火墙允许访问该端口
3. 检查日志：查看 addon 日志中的错误信息

## 更新

Addon 更新时，配置和数据会自动保留。更新步骤：

1. 在 Supervisor 中查看 addon 更新
2. 点击 **Update** 更新到新版本
3. 更新完成后，addon 会自动重启

## 卸载

卸载 addon 前，建议备份 `/data` 目录中的数据。卸载步骤：

1. 在 Supervisor 中停止 addon
2. 点击 **Uninstall** 卸载
3. 如需保留数据，在卸载前备份 `/data` 目录

## 技术支持

- **GitHub**: https://github.com/shuangyangyu/iptv
- **问题反馈**: 请在 GitHub Issues 中提交问题

## 许可证

本项目采用 MIT 许可证。
