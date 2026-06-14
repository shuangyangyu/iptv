# IPTV Server

IPTV Server 是一个用于生成 IPTV 播放列表和电子节目单的服务。它支持从运营商频道接口生成 `iptv.m3u`，从 EPG 接口生成 XMLTV 格式的 `epg.xml`，并内置 UDPXY 管理和回放代理能力。

## 文档索引

- `TECHNICAL.md`：技术架构、M3U/EPG 生成、UDPXY、回放代理和路由约束。
- `README_DOCKER.md`：Docker Compose 快速部署和源码构建。
- `README_DOCKERHUB.md`：Docker Hub 镜像使用、更新和排障。
- `README_HA部署.md`：在 Home Assistant 设备或同网段服务器上使用 Docker Compose 部署。
- `SETUP_DOCKERHUB.md`：GitHub Actions 推送 Docker Hub 镜像所需的 Secrets 配置。

## 当前架构

```text
iptv_sever/
├── api/                 # FastAPI 后端服务
│   ├── main.py          # 应用入口
│   ├── routers/         # REST API 路由
│   ├── services/        # 配置、任务、状态、cron、UDPXY 服务
│   ├── models/          # Pydantic 响应/请求模型
│   └── utils/           # 状态文件、网络工具
├── backend/             # M3U/EPG 生成核心逻辑
│   ├── core.py          # 频道解析、去重、M3U 生成
│   ├── epg.py           # EPG 抓取与 XMLTV 生成
│   ├── catchup.py       # 回放时间格式转换
│   ├── logo.py          # Logo 下载与本地化
│   ├── net.py           # 网络与源 IP 绑定工具
│   ├── udpxy_manager.py # UDPXY 进程管理
│   ├── build_m3u.py     # M3U 生成脚本
│   └── build_epg.py     # EPG 生成脚本
└── frontend/            # Vue 3 + Vite 控制台
    ├── src/views/       # 状态、配置、任务、日志、UDPXY 页面
    └── src/api/         # 前端 API 封装
```

## 核心功能

- M3U 生成：读取频道列表 JSON，抽取频道、分组、频道号、Logo 和回放信息。
- 组播转换：将 `rtp://` 或 `udp://` 播放地址转换为 UDPXY HTTP 地址。
- EPG 生成：请求节目单接口，按配置的回看/预告天数生成 XMLTV 文件。
- Logo 本地化：可下载频道 Logo，并将 M3U/EPG 中的 Logo 地址改为本地 `/out/logos/*`。
- UDPXY 管理：通过 API 和前端启动、停止、重启、查看 UDPXY 状态。
- 双网卡支持：`source_iface` 用于访问 IPTV 专网，`local_iface` 用于对外提供 Web/M3U/EPG/UDPXY 地址。
- 回放代理：接收播放器回放请求，转换时间格式后转发到实际回放服务。
- 定时任务：通过系统 `cron` 定期刷新 M3U/EPG。

## 数据流程

```text
频道列表接口 channel_5.js
    ↓
backend.core.load_channel_categories()
    ↓
backend.core.extract_channels()
    ↓
组播地址转换 + Logo 本地化 + 回放模板生成
    ↓
backend.core.generate_m3u_text()
    ↓
out/iptv.m3u

频道列表 + EPG 接口
    ↓
backend.epg.run_epg()
    ↓
backend.epg.build_xmltv()
    ↓
out/epg.xml
```

## Web 控制台

前端位于 `frontend/`，使用 Vue 3、Vue Router、Axios 和 Vite。

页面包括：

- `状态`：查看 M3U/EPG 文件、网络、cron、UDPXY 和回放配置状态。
- `配置`：管理频道源、网卡、EPG、Logo、定时任务、UDPXY 和回放配置。
- `任务`：手动触发 M3U/EPG 生成。
- `日志`：查看和清理应用日志。
- `UDPXY`：管理 UDPXY 服务。

## API 路由

后端入口是 `api/main.py`，默认挂载以下接口：

- `GET /health`：健康检查。
- `GET /api/v1/status`：系统状态。
- `GET /api/v1/config`、`PUT /api/v1/config`：配置读取和更新。
- `GET /api/v1/interfaces`、`GET /api/v1/interfaces/{name}`：网络接口信息。
- `POST /api/v1/jobs/{job_type}`：执行任务，`job_type` 支持 `m3u`、`epg`、`logos`。
- `GET /api/v1/logs`、`POST /api/v1/logs/clear`：日志读取和清理。
- `GET /api/v1/cron`、`POST /api/v1/cron`、`DELETE /api/v1/cron`：定时任务管理。
- `GET /api/v1/udpxy`：UDPXY 状态。
- `POST /api/v1/udpxy/actions`：UDPXY 操作，`action` 支持 `start`、`stop`、`restart`。
- `GET /api/v1/udpxy/config`、`PUT /api/v1/udpxy/config`：UDPXY 配置。
- `GET|POST /api/v1/catchup/{catchup_path}`：回放代理。

## 运行方式

### Docker Compose

项目根目录提供 `docker-compose.yml`：

```bash
docker-compose pull
docker-compose up -d
```

默认服务：

- 前端 nginx：`http://<host>:8088`
- API 文档：`http://<host>:8088/docs`
- M3U 文件：`http://<host>:8088/out/iptv.m3u`
- EPG 文件：`http://<host>:8088/out/epg.xml`
- UDPXY：`http://<host>:4022`

当前 compose 使用 host 网络模式：前端 nginx 对外监听 `8088`，后端 FastAPI 由 `API_PORT=8089` 运行，nginx 将 `/api`、`/out`、`/catchup`、`/health` 反代到后端。

### 本地开发

后端：

```bash
cd iptv_sever/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ../..
python3 -m uvicorn iptv_sever.api.main:app --host 0.0.0.0 --port 8089
```

前端：

```bash
cd iptv_sever/frontend
npm install
npm run dev
```

前端默认请求 `/api/v1`，生产环境由 nginx 反代；开发环境可按需要配置 Vite 代理。

### 命令行生成

生成 M3U：

```bash
python3 iptv_sever/backend/build_m3u.py \
  --input "http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js" \
  --out iptv_sever/out/iptv.m3u \
  --source-iface eth1 \
  --udpxy "http://192.168.1.250:4022" \
  --web-base-url "http://192.168.1.250:8088"
```

生成 EPG：

```bash
python3 iptv_sever/backend/build_epg.py \
  --channels-url "http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js" \
  --out iptv_sever/out/epg.xml \
  --source-iface eth1 \
  --days-back 0 \
  --days-forward 7 \
  --web-base-url "http://192.168.1.250:8088"
```

## 配置与状态

标准环境下：

- 输出目录：`iptv_sever/out`
- 状态文件：`iptv_sever/api/state.json`
- API 日志：`iptv_sever/api/api.log`

主要配置字段：

- `input_url`：频道列表接口。
- `source_iface`：IPTV 专网网卡。
- `local_iface`：本地服务网卡。
- `output_m3u`：M3U 输出文件名。
- `epg_out`：EPG 输出文件名。
- `epg_base_url`、`epg_riddle`、`epg_time_ms`：EPG 请求参数。
- `epg_days_back`、`epg_days_forward`：EPG 日期范围。
- `download_logos`、`localize_logos`：Logo 下载和本地化。
- `udpxy`：UDPXY 端口、绑定地址、最大连接数等配置。
- `catchup`：回放目标服务地址和虚拟域名。

## 网络说明

IPTV 场景通常存在两个网络出口：

- 上网/局域网口：用于访问 Web 控制台、播放器拉取 M3U/EPG/Logo。
- IPTV 专网口：用于访问运营商频道源、EPG 和组播流。

因此应用需要区分：

- `source_iface`：绑定请求源 IP，访问 IPTV 专网资源。
- `local_iface`：生成对外访问地址，例如 `http://192.168.1.250:8088/out/iptv.m3u` 和 `http://192.168.1.250:4022/rtp/...`。

## 回放代理

M3U 中可生成类似下面的回放模板：

```m3u
#EXTINF:-1 catchup="default" catchup-source="http://192.168.1.250:8088/catchup/ZTE_EPG16/2/9201?programbegin={start}&programend={end}" tvg-id="387",频道名
http://192.168.1.250:4022/rtp/239.33.5.3:22590
```

播放器请求回放时，后端会：

1. 识别 `programbegin/programend` 或 `start/end`。
2. 支持 Unix 秒、Unix 毫秒、ISO 8601、`YYYYMMDDHHmmss`、`YYYYMMDDHHmmss+00`。
3. 转换为目标回放接口需要的时间格式。
4. 按 `catchup.target_host`、`catchup.target_port`、`catchup.virtual_domain` 转发请求。

## 相关文档

- 技术文档：`TECHNICAL.md`
- Docker 部署：`README_DOCKER.md`
- Docker Hub 镜像：`README_DOCKERHUB.md`
- Home Assistant / 服务器部署：`README_HA部署.md`
- Docker Hub Secrets 配置：`SETUP_DOCKERHUB.md`
