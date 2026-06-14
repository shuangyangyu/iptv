# IPTV Server 技术文档

本文档说明 IPTV Server 的设计原理、核心流程、模块职责和部署运行逻辑。当前项目以 Docker Compose 为主要部署方式，由 FastAPI 后端、Vue 前端、Nginx 反向代理、UDPXY 和若干生成脚本组成。

## 1. 设计目标

IPTV Server 解决的是 IPTV 专网资源与普通播放器之间的适配问题：

- 将运营商频道列表接口转换为播放器可识别的 M3U 播放列表。
- 将运营商 EPG 接口转换为标准 XMLTV 节目单。
- 将 `rtp://`、`udp://` 组播流转换为播放器可访问的 HTTP 地址。
- 自动生成对外可访问的 M3U、EPG、Logo 和回放代理地址。
- 通过 Web 控制台管理配置、任务、日志、网络接口和 UDPXY 服务。

典型使用场景是双网卡环境：

- `source_iface` 连接 IPTV 专网，用于访问频道源、EPG 接口和组播流。
- `local_iface` 连接家庭局域网，用于给播放器提供 Web、M3U、EPG、Logo 和 UDPXY 地址。

## 2. 总体架构

```text
播放器 / 浏览器
    ↓
Nginx 前端容器（8088）
    ├── /                 → Vue 静态页面
    ├── /api/*            → FastAPI 后端（8089）
    ├── /out/*            → FastAPI 静态输出目录
    ├── /catchup/*        → FastAPI 回放代理
    └── /health           → FastAPI 健康检查

FastAPI 后端
    ├── 配置与状态：state.json
    ├── 任务执行：build_m3u.py / build_epg.py
    ├── UDPXY 管理：udpxy 进程
    ├── 网络接口探测：source_iface / local_iface
    └── 输出目录：out/iptv.m3u、out/epg.xml、out/logos/*

IPTV 专网 / 运营商接口
    ├── 频道列表接口 channel_5.js
    ├── EPG 节目单接口
    ├── 组播流 rtp:// 或 udp://
    └── 回放接口
```

## 3. 运行时组件

### 3.1 Docker Compose

`docker-compose.yml` 定义两个服务：

- `backend`：使用 `shuangyangyu/iptv-backend:latest`，运行 FastAPI、任务脚本、cron 和 UDPXY 管理逻辑。
- `frontend`：使用 `shuangyangyu/iptv-frontend:latest`，运行 Nginx 和 Vue 构建产物。

当前默认使用 `network_mode: host`，原因是 IPTV 场景通常需要访问主机网络接口和组播网络。`backend` 使用 `API_PORT=8089`，`frontend` 的 Nginx 对外监听 `8088` 并反代后端。

持久化数据通过 Docker volume 保存：

- `iptv_out_data` → `/app/iptv_sever/out`
- `iptv_state_data` → `/app/iptv_sever/api`

### 3.2 容器启动

`docker-entrypoint.sh` 是后端容器入口：

1. 启动 `cron` 或 `crond`，用于定时任务。
2. 检查 cron 进程是否存在，失败只记录警告，不阻止 API 启动。
3. 通过 `uvicorn iptv_sever.api.main:app` 启动 FastAPI。
4. 端口来自 `API_PORT` 环境变量，默认值为 `8088`，当前 Compose 中设置为 `8089`。

### 3.3 Nginx 入口

`nginx.conf` 统一对外暴露 `8088`：

- `/`：前端单页应用，使用 `try_files` 回退到 `index.html`。
- `/api`：反向代理到 `localhost:8089`。
- `/out`：反向代理到 FastAPI 静态文件服务。
- `/catchup`：反向代理到回放代理，超时时间更长。
- `/health`：反向代理到后端健康检查。

## 4. 后端服务结构

后端入口是 `iptv_sever/api/main.py`。它创建 FastAPI 应用，挂载 `/out` 静态文件目录，并注册以下路由模块：

- `status`：系统状态。
- `config`：配置读取和更新。
- `interfaces`：网络接口信息。
- `jobs`：M3U、EPG 任务触发。
- `logs`：任务日志。
- `cron`：系统 cron 管理。
- `system`：环境检查。
- `catchup`：回放代理。
- `udpxy`：UDPXY 状态和操作。

配置路径由 `iptv_sever/api/config.py` 定义：

- `OUT_DIR`：`iptv_sever/out`
- `STATE_PATH`：`iptv_sever/api/state.json`
- `LOG_FILE`：`iptv_sever/api/api.log`

## 5. 状态与配置模型

应用没有使用数据库，状态保存在 JSON 文件中。默认配置由 `iptv_sever/api/utils/state.py` 的 `default_state()` 提供，结构包含：

- `config`：频道源、网卡、M3U/EPG、Logo、cron、UDPXY、回放配置。
- `status`：输出文件状态和最近一次任务状态。
- `logs`：最近任务日志，最多保留 400 条。

配置读取逻辑在 `iptv_sever/api/services/state.py`：

1. 读取 `state.json`。
2. 与默认配置合并，避免字段缺失。
3. 强制 `use_udpxy=True`，因为当前播放链路默认依赖 UDPXY。
4. 基于 `local_iface` 自动生成：
   - `web_base_url`，例如 `http://192.168.1.250:8088`
   - `udpxy_base`，例如 `http://192.168.1.250:4022`
5. `x_tvg_url` 不作为持久配置返回，而是在生成 M3U 时动态计算。

配置更新采用白名单方式，只允许更新明确列出的字段，避免前端或外部调用写入未知结构。

## 6. M3U 生成原理

M3U 生成由 `iptv_sever/backend/build_m3u.py` 串联，核心逻辑在 `iptv_sever/backend/core.py`。

### 6.1 输入

主要输入来自频道列表接口，例如：

```text
http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js
```

该接口返回分类数组，每个分类通常包含 `channelList`。

### 6.2 频道解析

`load_channel_categories()` 负责：

1. 校验输入必须是 URL。
2. 使用可选 opener 发起请求，opener 可绑定 `source_iface` 对应 IP。
3. 将响应按 UTF-8 解码。
4. 解析 JSON，并要求根节点为数组。

`extract_channels()` 负责：

1. 处理分类名字段兼容：`category_name`、`categoryName`、`name`。
2. 优先使用“全部”分类，避免同一频道在多个分类里重复输出。
3. 如果“全部”分类缺少真实分组，则先遍历非“全部”分类建立频道到分组的映射。
4. 抽取频道字段：
   - `name`
   - `primaryid` 或指定 `tvg_id_field`
   - `channelnumber`
   - `fileurl`
   - `multi_ZX`
   - `zx`
5. 使用 `tvg_id` 优先去重，缺失时用 `name|multi_ZX` 去重。
6. 从 `zx` 字段提取回放目标服务器、端口和 `virtualDomain`。
7. 如果传入 `web_base_url`，生成播放器可用的 `catchup-source` 模板。

### 6.3 组播到 HTTP 转换

播放器通常不能直接播放 IPTV 组播地址，因此需要 UDPXY：

```text
rtp://239.33.5.3:22590
    ↓
http://192.168.1.250:4022/rtp/239.33.5.3:22590
```

`convert_multicast_to_udpxy()` 支持：

- `rtp://...` → `{udpxy_base}/rtp/...`
- `udp://...` → `{udpxy_base}/udp/...`
- 其他协议保持原样。

### 6.4 M3U 输出

`generate_m3u_text()` 生成最终 M3U：

1. 第一行写入 `#EXTM3U`。
2. 如果存在 EPG 地址，则写入 `#EXT-X-TVG url-tvg="..."`。
3. 每个频道输出：
   - `#EXTINF:-1`
   - `catchup` / `catchup-source`
   - `tvg-id`
   - `tvg-name`
   - `tvg-logo`
   - `group-title`
   - `tvg-chno`
   - 下一行播放地址。

输出文件默认是 `out/iptv.m3u`。

## 7. EPG 生成原理

EPG 生成由 `iptv_sever/backend/build_epg.py` 串联，核心逻辑在 `iptv_sever/backend/epg.py`。

### 7.1 输入

EPG 生成需要：

- 频道列表接口，用于得到频道 ID。
- EPG 查询接口。
- `riddle` 和 `time` 等接口参数。
- `days_back` 和 `days_forward`，控制保留日期范围。

### 7.2 节目单请求

`fetch_program_list()` 对每个频道发起 POST 请求：

1. 组装 `channelId`、`riddle`、`time` 和额外参数。
2. 使用 `application/x-www-form-urlencoded` 提交。
3. 使用可选 opener 绑定源 IP。
4. 返回 JSON 数据或错误信息。

### 7.3 日期过滤

`filter_epg_by_days()` 按中国时区计算日期范围：

```text
start = today - days_back
end   = today + days_forward
```

只保留 `YYYYMMDD` 落在范围内的节目数据。

### 7.4 XMLTV 构建

XMLTV 时间使用 `YYYYMMDDHHMMSS +0800` 格式。节目结束时间通过以下优先级计算：

1. 优先使用 `duration=HHMMSS`。
2. 其次使用 `endTime`。
3. 如果结束时间小于开始时间，则按跨天处理。

最终输出默认是 `out/epg.xml`。

## 8. 任务执行逻辑

前端或外部客户端调用：

```text
POST /api/v1/jobs/{job_type}
```

`job_type` 支持：

- `m3u`
- `epg`
- `logos`

`iptv_sever/api/services/job.py` 的 `execute_job()` 负责执行：

1. 读取状态文件和配置。
2. 基于 `local_iface` 生成 `web_base_url`。
3. 基于 `local_iface` 和 UDPXY 端口生成 `udpxy_base`。
4. 根据任务类型选择脚本：
   - `backend/build_m3u.py`
   - `backend/build_epg.py`
5. 使用 `subprocess.run()` 执行脚本，超时为 300 秒。
6. 捕获 stdout/stderr，写入任务日志。
7. 更新 `status.last_job`、`last_job_rc`、`last_job_at`。
8. 如果生成成功，实时检查输出文件大小和更新时间。
9. M3U 生成成功后，会再次解析频道列表，尝试提取回放服务器配置并保存。

`logos` 当前不是独立下载任务，而是提示 Logo 会在生成 M3U 时自动处理。

## 9. UDPXY 管理逻辑

UDPXY 是组播转 HTTP 的关键组件。管理逻辑分两层：

- API 层：`iptv_sever/api/services/udpxy.py`
- 进程层：`iptv_sever/backend/udpxy_manager.py`

API 提供：

- `GET /api/v1/udpxy`
- `POST /api/v1/udpxy/actions`
- `GET /api/v1/udpxy/config`
- `PUT /api/v1/udpxy/config`

`get_udpxy_config()` 会从 `state.json` 合并默认值，并始终让 UDPXY 的 `source_iface` 与顶层 `source_iface` 同步。UDPXY 进程本身只直接使用 `source_iface`：启动命令中的 `-m` 参数会绑定到该接口，用来接收 IPTV 组播流。`local_iface` 不会传给 UDPXY 进程，它用于生成播放器访问 UDPXY 的 `udpxy_base`。

典型启动参数如下：

```bash
udpxy -p 4022 -a 0.0.0.0 -m eth1 -c 5
```

其中 `-m eth1` 来自 `source_iface`，`-a 0.0.0.0` 表示监听所有本地地址，播放器最终访问的地址由 `local_iface` 的 IP 和 UDPXY 端口组合得到。

启动流程：

1. 读取 UDPXY 配置。
2. 检查系统是否存在 `udpxy` 命令。
3. 构造并启动 UDPXY 进程。
4. 保存 PID、记录日志。
5. API 在启动后短暂等待并重试检查运行状态。

## 10. 回放代理逻辑

回放代理解决的是播放器回放请求与运营商回放接口之间的适配问题。播放器通常只知道节目开始/结束时间，并会把时间填入 M3U 的 `catchup-source` 模板；运营商接口则可能要求固定路径、固定参数名、固定时间格式和 `virtualDomain` 参数。项目通过 `/catchup/*` 代理把这两者接起来。

### 10.1 回放信息来源

频道列表中每个频道可能包含 `zx` 字段。`iptv_sever/backend/core.py` 在解析频道时会读取这个字段：

```text
zx = http://10.255.129.26:6060/ZTE_EPG16/2/9201?virtualDomain=hls.tvod_hls.zte.com
```

解析过程会提取三类信息：

- `catchup_path`：路径部分，例如 `ZTE_EPG16/2/9201`。
- `catchup_host` 和 `catchup_port`：目标回放服务器，例如 `10.255.129.26:6060`。
- `virtual_domain`：查询参数里的 `virtualDomain`。

M3U 生成时只把路径写进播放器可访问的代理地址；目标服务器地址不直接暴露给播放器。M3U 生成完成后，任务服务会再次解析频道列表，并把提取到的目标回放配置保存到 `state.json` 的 `config.catchup`：

```json
{
  "catchup": {
    "target_host": "10.255.129.26",
    "target_port": 6060,
    "virtual_domain": "hls.tvod_hls.zte.com"
  }
}
```

### 10.2 M3U 模板生成

如果频道存在有效的 `zx` 字段，并且生成 M3U 时传入了 `web_base_url`，系统会为频道生成 `catchup-source`：

```m3u
#EXTINF:-1 catchup="default" catchup-source="http://192.168.1.250:8088/catchup/ZTE_EPG16/2/9201?programbegin={start}&programend={end}" tvg-id="387",频道名
http://192.168.1.250:4022/rtp/239.33.5.3:22590
```

这里有几个关键点：

- `catchup="default"`：使用播放器默认回放模式，当前主要面向 TiviMate 一类播放器。
- `catchup-source`：播放器发起回放请求时访问的 URL 模板。
- `{start}` 和 `{end}`：播放器运行时替换的占位符。
- `/catchup/...`：对外暴露的代理路径，不是运营商真实回放地址。
- `programbegin`、`programend`：代理服务接收的标准参数名。

`web_base_url` 由 `local_iface` 计算得到，所以回放代理地址应该是播放器能访问的局域网地址，例如 `http://192.168.1.250:8088`。

### 10.3 外部路径和内部路由

外部播放器访问的是：

```text
http://192.168.1.250:8088/catchup/{catchup_path}?programbegin=...&programend=...
```

Nginx 负责把 `/catchup` 转发到后端 FastAPI：

```text
/catchup/*  →  http://localhost:8089/catchup/*
```

FastAPI 实际注册的路由在 `iptv_sever/api/routers/catchup.py`：

```text
GET|POST /api/v1/catchup/{catchup_path}
```

当前前端 API 默认都走 `/api/v1`，但外部回放入口走 `/catchup`。部署时需要保证 Nginx 对 `/catchup` 的反向代理配置与后端路由前缀一致；否则播放器请求会到达 Nginx，但无法命中后端回放路由。

### 10.4 请求参数兼容

回放代理支持两组时间参数：

- `programbegin` / `programend`
- `start` / `end`

处理顺序是：

1. 优先读取 `programbegin` 和 `programend`。
2. 如果不存在，再读取 `start` 和 `end`。
3. 对参数做 URL 解码。
4. 如果仍然是 `{start}` 或 `{end}`，直接返回 400，表示播放器没有替换占位符。
5. 其他 query 参数会被保留下来，并继续传给目标回放接口。

示例：

```text
/catchup/ZTE_EPG16/2/9201?programbegin=1735293000&programend=1735293240
```

或：

```text
/catchup/ZTE_EPG16/2/9201?start=2025-12-27T08:50:00Z&end=2025-12-27T08:54:00Z
```

### 10.5 时间格式识别

`iptv_sever/backend/catchup.py` 的 `detect_time_format()` 支持以下输入：

| 类型 | 示例 | 说明 |
| --- | --- | --- |
| Unix 秒 | `1735293000` | 10 位数字 |
| Unix 毫秒 | `1735293000000` | 13 位数字 |
| ISO 8601 | `2025-12-27T08:50:00Z` | UTC 时间 |
| 紧凑时间 | `20251227085000` | 无时区，代码按 UTC+8 处理 |
| 带时区紧凑时间 | `20251227085000+00` | 带时区后缀 |

无法识别时，接口返回 400，并在日志里记录原始参数。

### 10.6 时间格式转换

目标回放接口需要的时间格式是：

```text
YYYYMMDDHHmmss+00
```

转换逻辑由 `convert_to_zte_format()` 完成：

- Unix 秒/毫秒：按 UTC 时间戳转换。
- ISO 8601：解析后转换为 UTC。
- `YYYYMMDDHHmmss`：按北京时间 UTC+8 理解，再转换为 UTC。
- `YYYYMMDDHHmmss+00`：解析时区后转换为 UTC。

例如播放器传入：

```text
programbegin=1735293000
programend=1735293240
```

代理会转换成类似：

```text
programbegin=20241227085000+00
programend=20241227085400+00
```

实际写入目标 URL 时，`+` 会编码为 `%2B`，避免被 HTTP query 解析为空格：

```text
programbegin=20241227085000%2B00
```

### 10.7 目标 URL 构建

`build_catchup_url()` 将代理请求转换为运营商回放请求：

```text
http://{target_host}:{target_port}/{catchup_path}?programbegin={begin_zte}&programend={end_zte}&virtualDomain={virtual_domain}
```

示例：

```text
http://10.255.129.26:6060/ZTE_EPG16/2/9201?programbegin=20241227085000%2B00&programend=20241227085400%2B00&virtualDomain=hls.tvod_hls.zte.com
```

参数来源：

- `target_host`：`config.catchup.target_host`
- `target_port`：`config.catchup.target_port`
- `virtualDomain`：`config.catchup.virtual_domain`
- `catchup_path`：播放器请求路径中的剩余部分
- `programbegin/programend`：由播放器时间转换得到

额外参数会继续透传，但 `programbegin`、`programend`、`virtualDomain` 会由代理统一生成，避免被外部覆盖。

### 10.8 请求转发和响应返回

FastAPI 回放路由使用 `urllib.request` 转发请求。转发时会：

1. 使用播放器请求中的 `User-Agent`，没有则使用默认浏览器 UA。
2. 创建 redirect handler，保留对 302 重定向的处理。
3. 读取目标服务器响应内容。
4. 将响应体、状态码和响应头返回给播放器。
5. 如果目标服务器返回 HTTP 错误，则把错误状态码和响应体继续返回。

这意味着回放接口可能返回：

- 302 重定向。
- m3u8 播放列表。
- TS 分片内容。
- 运营商错误页面或空响应。

代理层原则上不解析媒体内容，只负责时间转换和请求转发。

### 10.9 与 EPG 的关系

回放能否在播放器里显示和播放，依赖两个条件：

1. M3U 中存在 `catchup` 和 `catchup-source`。
2. EPG 中存在该频道对应时间段的节目数据。

播放器通常从 EPG 中选择节目，再把节目开始/结束时间填入 M3U 的 `catchup-source`。如果 EPG 缺失或 `tvg-id` 不匹配，播放器可能不会显示回放入口，即使代理服务本身正常。

因此排查回放时要同时检查：

- M3U 频道的 `tvg-id`。
- EPG 中对应 `<channel id="...">` 和 `<programme channel="...">`。
- M3U 中是否包含 `catchup-source`。
- 播放器是否真的发起了 `/catchup/...` 请求。

### 10.10 常见故障判断

| 现象 | 可能原因 | 检查点 |
| --- | --- | --- |
| 播放器没有回放入口 | EPG 缺失或 `tvg-id` 不匹配 | 检查 `epg.xml` 和 M3U 的 `tvg-id` |
| 请求返回 400：时间参数未替换 | 播放器未替换 `{start}` / `{end}` | 检查播放器是否支持 `catchup-source` 模板 |
| 请求返回 400：无法识别时间格式 | 播放器传入了未支持的时间格式 | 查看 `api.log` 中原始参数 |
| 请求返回 500：转发失败 | 目标回放服务器不可达 | 在服务器上测试 `10.255.129.26:6060` 是否可访问 |
| 回放请求到达但无法播放 | 运营商返回重定向或 m3u8 异常 | 查看响应状态码和内容类型 |
| 代理开启后回放失败 | `/catchup` 或 `4022` 没有走局域网直连 | 代理规则中强制 IPTV Server IP 直连 |

### 10.11 手动测试

可以直接用浏览器或 curl 测试代理入口：

```bash
curl -v "http://192.168.1.250:8088/catchup/ZTE_EPG16/2/9201?programbegin=1735293000&programend=1735293240"
```

也可以测试 ISO 时间：

```bash
curl -v "http://192.168.1.250:8088/catchup/ZTE_EPG16/2/9201?programbegin=2025-12-27T08:50:00Z&programend=2025-12-27T08:54:00Z"
```

如果只想验证时间转换逻辑，应先查看日志中是否出现：

```text
收到回放请求
原始 programbegin
转换后 programbegin
转发到
```

如果日志里没有这些内容，说明请求没有到达后端，优先检查 Nginx `/catchup` 反向代理、播放器访问地址和代理/VPN 直连规则。

## 11. 前端实现逻辑

前端位于 `iptv_sever/frontend`，使用：

- Vue 3
- Vue Router
- Axios
- TypeScript
- Vite

`src/api/index.ts` 创建 Axios 实例：

- `baseURL=/api/v1`
- 超时 30 秒
- 响应拦截器直接返回 `response.data`
- 错误响应统一转换为 `{ message, detail, status }`

路由页面：

- `/`：状态页。
- `/config`：配置页。
- `/jobs`：任务页。
- `/logs`：日志页。
- `/udpxy`：UDPXY 页。

状态页会并行加载状态、配置、网络接口和 cron 信息。配置页负责编辑主要配置，保存后调用 `PUT /api/v1/config`。

## 12. 网络接口与地址生成

项目中有两个关键地址：

- `web_base_url`：播放器访问 Web、M3U、EPG、Logo、回放代理使用。
- `udpxy_base`：播放器访问组播转 HTTP 流使用。

两者都依赖 `local_iface` 获取本地局域网 IP：

```text
web_base_url = http://{local_iface_ip}:8088
udpxy_base   = http://{local_iface_ip}:4022
```

如果无法获取 `local_iface` IP，会回退到默认 `192.168.1.250`。这意味着部署后应优先在配置页确认 `local_iface` 是否正确。

`source_iface` 用于访问 IPTV 专网资源，主要影响：

- 频道列表接口请求。
- EPG 接口请求。
- UDPXY 监听/转发组播流时使用的源接口。

因此两张网卡的分工可以理解为：`source_iface` 是 UDPXY 的输入接口，负责接收 IPTV 组播；`local_iface` 是对外访问地址来源，负责让局域网播放器访问 `http://{local_iface_ip}:4022/...`。

## 13. 定时任务

后端容器启动时会尝试启动 cron 服务。API 层通过 `iptv_sever/api/services/cron.py` 管理系统 crontab：

- `GET /api/v1/cron`：检查当前 crontab 是否包含生成任务。
- `POST /api/v1/cron`：调用 `backend/setup_cron.sh` 设置任务。
- `DELETE /api/v1/cron`：移除任务。

cron 失败不会阻止 FastAPI 启动，只会导致定时刷新不可用。

## 14. 日志与可观测性

应用日志分两类：

- Python logging 输出到 stdout 和 `iptv_sever/api/api.log`。
- 任务日志保存在 `state.json` 的 `logs` 数组中。

任务日志通过 `append_log()` 写入，最多保留最近 400 条，前端日志页面通过 API 展示。

状态接口实时检查：

- M3U 文件是否存在、大小、mtime、下载地址。
- EPG 文件是否存在、大小、mtime、下载地址。
- UDPXY 当前运行状态。
- 最近一次任务名称、返回码和时间。

## 15. 关键约束

- 当前默认依赖 UDPXY，`use_udpxy` 会被强制视为启用。
- `state.json` 是普通 JSON 文件，不是数据库；并发写入可能存在覆盖风险。
- 默认 CORS 为 `allow_origins=["*"]`，如果暴露到公网需要增加认证和访问控制。
- Docker Compose 默认 host 网络模式更适合 Linux；macOS/Windows 使用 bridge 时需要调整 Nginx 后端地址。
- EPG 和频道接口依赖运营商专网和抓包参数，参数变化会导致生成失败。

## 16. 常见扩展点

- 增加认证：可在 FastAPI 中添加鉴权依赖，或在 Nginx 层加 Basic Auth / 反向代理认证。
- 改进状态存储：可将 `state.json` 替换为 SQLite，避免并发写入覆盖。
- 增加任务队列：当前任务同步执行，可改为后台队列并返回 job id。
- 支持更多频道源格式：可在 `backend/core.py` 增加输入解析适配层。
- 增加测试：建议优先覆盖频道解析、M3U 生成、EPG 时间计算、回放时间转换和状态合并。

## 17. 主要文件索引

- `docker-compose.yml`：生产部署编排。
- `Dockerfile.backend`：后端镜像构建。
- `Dockerfile.frontend`：前端镜像构建。
- `docker-entrypoint.sh`：后端容器入口。
- `nginx.conf`：前端 Nginx 和反向代理配置。
- `iptv_sever/api/main.py`：FastAPI 入口。
- `iptv_sever/api/services/job.py`：任务执行。
- `iptv_sever/api/services/state.py`：配置和状态服务。
- `iptv_sever/api/services/udpxy.py`：UDPXY API 服务。
- `iptv_sever/backend/core.py`：M3U 核心逻辑。
- `iptv_sever/backend/epg.py`：EPG/XMLTV 核心逻辑。
- `iptv_sever/backend/catchup.py`：回放时间转换和目标 URL 构建。
- `iptv_sever/backend/udpxy_manager.py`：UDPXY 进程管理。
- `iptv_sever/frontend/src/api/index.ts`：前端 API 客户端。
- `iptv_sever/frontend/src/router/index.ts`：前端路由。
