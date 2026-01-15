# iptv_sever - IPTV M3U/EPG 生成工具

IPTV Server 是一个用于生成 IPTV 播放列表（M3U）和电子节目单（EPG）的工具集。

## 项目结构

```
iptv_sever/
├── backend/          # 核心业务逻辑
│   ├── core.py       # M3U 生成核心逻辑
│   ├── epg.py        # EPG 生成逻辑
│   ├── catchup.py    # 回放功能支持
│   ├── logo.py       # Logo 下载与本地化
│   ├── net.py        # 网络工具（IP 绑定、URL 处理）
│   ├── conf.py       # 配置和默认值
│   ├── build_m3u.py  # M3U 生成入口脚本
│   └── build_epg.py  # EPG 生成入口脚本
└── web/              # Web 控制台（Flask）
    ├── app.py        # Flask 应用
    ├── templates/    # HTML 模板
    └── static/       # 静态资源（CSS/JS）
```

## 核心功能

### M3U 生成
- 从频道列表 JSON 生成 M3U 播放列表
- 支持组播地址转换为 UDPXY HTTP 地址
- 自动下载并本地化频道 Logo
- 支持回放（Catch-up）功能配置

### EPG 生成
- 从 EPG 接口抓取节目单数据
- 生成标准 XMLTV 格式（epg.xml）
- 支持时间范围过滤（回看/预告天数）

### Web 控制台
- 提供图形化界面进行配置和管理
- 支持一键生成 M3U 和 EPG
- 实时查看任务状态和日志
- 支持定时任务配置

## 数据流程

```text
频道列表 JSON (channel_5.js)
    ↓
core.py: load_channel_categories()
    ↓
core.py: extract_channels()
    ↓
core.py: generate_m3u_text()
    ↓
输出 M3U 文件 (iptv.m3u)
    ↓
EPG 接口抓取
    ↓
epg.py: build_xmltv()
    ↓
输出 EPG 文件 (epg.xml)
```

## 模块职责

### backend/conf.py
- 定义所有默认配置值（`DEFAULT_*`）
- 定义配置数据结构（`M3USettings`, `EPGSettings`）

### backend/net.py
- `is_url()` - 判断是否为 HTTP URL
- `get_ipv4_from_iface()` - 从指定网卡获取 IPv4 地址
- `build_opener()` - 构建 urllib opener（可绑定源 IP）

### backend/core.py
- `load_channel_categories()` - 从 URL 加载频道列表 JSON
- `extract_channels()` - 抽取频道数据并去重
- `convert_multicast_to_udpxy()` - 组播地址转 UDPXY HTTP
- `generate_m3u_text()` - 生成 M3U 文本内容
- `write_text()` - 写入文件

### backend/epg.py
- `run_epg()` - 抓取 EPG 节目单 JSON
- `build_xmltv()` - 生成 XMLTV 格式文件
- `filter_epg_by_days()` - 按日期范围过滤节目

### backend/logo.py
- `localize_logos()` - 下载 Logo 并重写为本地 URL

### backend/catchup.py
- `build_catchup_url()` - 构建回放 URL
- 时间格式转换（Unix/ISO/ZTE 格式）

## 使用方式

### 方式一：Web 控制台（推荐）

通过 Web 界面进行配置和生成，访问地址：`http://192.168.1.250:8088`

#### 安装和运行

**方法一：使用启动脚本（推荐，自动处理虚拟环境）**

```bash
cd iptv_sever/web
chmod +x start.sh
./start.sh
```

脚本会自动创建虚拟环境、安装依赖并启动 Flask。

**方法二：手动使用虚拟环境**

如果遇到 `externally-managed-environment` 错误（macOS Homebrew Python），使用虚拟环境：

```bash
cd iptv_sever/web

# 如果虚拟环境不存在，创建它
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
python3 -m pip install -r requirements.txt

# 启动
python3 app.py
```

**方法三：OpenWrt 路由器上安装**

在 OpenWrt 上，需要先安装 pip 和依赖：

```bash
# 使用安装脚本（推荐）
cd /www/iptv_sever/web
chmod +x install_openwrt.sh
./install_openwrt.sh

# 或手动安装
opkg update
opkg install python3-pip
cd /www/iptv_sever/web
pip3 install -r requirements.txt
python3 app.py
```

**注意：**
- OpenWrt 上可能不支持 `venv` 模块，直接使用系统 Python
- 启动时建议修改 `app.py` 中的 `host="0.0.0.0"` 以便局域网访问
- 如果遇到权限问题，可能需要使用 `--user` 参数：`pip3 install --user -r requirements.txt`

#### 服务管理（路由器环境）

在路由器环境中，建议使用服务管理脚本来启动和停止 IPTV Server。

**启动服务：**

```bash
/www/iptv_sever/start_service.sh
```

**停止服务：**

```bash
/www/iptv_sever/stop_service.sh
```

**查看服务状态：**

```bash
# 检查进程是否运行
ps aux | grep "python3.*app.py"

# 检查端口是否监听
netstat -tlnp | grep 8088
# 或
ss -tlnp | grep 8088
```

**查看日志：**

```bash
# 实时查看服务日志
tail -f /www/iptv_sever/web/service.log

# 查看应用日志（Flask 日志）
tail -f /www/iptv_sever/web/app.log
```

**开机自启动（OpenWrt）：**

创建 `/etc/init.d/iptv_server`：

```bash
#!/bin/sh /etc/rc.common
# IPTV Server 服务

START=99
STOP=10

start_service() {
    /www/iptv_sever/start_service.sh
}

stop_service() {
    /www/iptv_sever/stop_service.sh
}

restart() {
    stop_service
    sleep 2
    start_service
}
```

然后启用服务：

```bash
chmod +x /etc/init.d/iptv_server
/etc/init.d/iptv_server enable
/etc/init.d/iptv_server start
```

#### Web 控制台功能

- **总览**：查看 M3U/EPG 文件状态、定时任务状态
- **配置**：管理 M3U/EPG 生成参数、定时任务配置
- **日志**：查看任务执行日志
- **一键生成**：快速生成 M3U 和 EPG 文件
- **主题切换**：支持暗色/亮色主题（本地保存）

### 方式二：命令行脚本

#### 生成 M3U

```bash
python3 iptv_sever/backend/build_m3u.py \
  --input 'http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js' \
  --out /www/iptv_sever/web/out/iptv.m3u \
  --source-iface eth1
```

#### 生成 EPG

```bash
python3 iptv_sever/backend/build_epg.py \
  --source-iface eth1 \
  --days-back 6 \
  --days-forward 0
```

## 重要说明

### 为什么必须指定 source-iface？

IPTV 通常使用双出口网络：
- 上网口：访问互联网
- IPTV 口：访问 IPTV 专网（如 `10.255.x.x`）

不绑定网卡时，系统可能走默认上网口，导致 IPTV 专网不可达。因此需要明确指定 IPTV 网卡（如 `eth1`），系统会从该网卡获取 IP 并绑定所有网络请求。

### 回放功能

项目支持 TiviMate 播放器的回放（Catch-up）功能：
- M3U 中包含 `catchup-source` 属性
- EPG 提供节目时间信息
- 通过 Web 控制台的代理服务处理时间格式转换

#### 回放代理服务

Flask 服务中已添加了**回放代理服务**，用于解决 TiviMate 时间格式与 ZTE_EPG16 服务端格式不匹配的问题。

**工作原理：**

```
TiviMate 播放器
  ↓ (发送回放请求，可能包含各种时间格式)
  http://192.168.1.250:8088/catchup/ZTE_EPG16/2/9201?programbegin=...&programend=...
  ↓
Flask 代理服务（时间格式转换）
  ↓ (检测时间格式并转换)
  1. 检测 TiviMate 发送的时间格式（ISO 8601、Unix 时间戳等）
  2. 转换为 ZTE_EPG16 需要的格式（YYYYMMDDHHmmss+00）
  3. URL 编码（+ 号编码为 %2B）
  ↓ (转发请求)
  http://10.255.129.26:6060/ZTE_EPG16/2/9201?programbegin=20251227085000%2B00&programend=...
  ↓
ZTE_EPG16 服务端
  ↓ (返回响应)
  302 重定向或 m3u8 播放列表
  ↓
Flask 代理服务
  ↓ (转发响应)
  原样返回给 TiviMate
  ↓
TiviMate 播放器
```

**支持的时间格式：**

| 格式类型 | 示例 | 说明 |
|---------|------|------|
| **Unix 时间戳（秒）** | `1735293000` | 10位数字 |
| **Unix 时间戳（毫秒）** | `1735293000000` | 13位数字 |
| **ISO 8601** | `2025-12-27T08:50:00Z` | 标准格式，带分隔符 |
| **YYYYMMDDHHmmss** | `20251227085000` | 紧凑格式，无时区 |
| **YYYYMMDDHHmmss+00** | `20251227085000+00` | 紧凑格式，带时区 |

**M3U 配置示例：**

```m3u
#EXTINF:-1 catchup="default" catchup-source="http://192.168.1.250:8088/catchup/ZTE_EPG16/2/9201?programbegin={start}&programend={end}" tvg-id="387" ...
http://192.168.1.250:4022/rtp/239.33.5.3:22590
```

**注意：**
- `{start}` 和 `{end}` 是 TiviMate 的占位符，会被自动替换
- 代理服务会自动检测并转换时间格式
- 最终会转发到实际的回放接口（`10.255.129.26:6060`）

**测试方法：**

```bash
# 测试 Unix 时间戳（秒）
curl "http://192.168.1.250:8088/catchup/ZTE_EPG16/2/9201?programbegin=1735293000&programend=1735293240"

# 查看日志
tail -f /www/iptv_sever/web/app.log | grep catchup
```

**故障排查：**

1. **时间格式转换失败**
   - 检查日志中的原始时间参数
   - 确认时间格式是否在支持列表中

2. **转发请求失败**
   - 检查目标回放接口是否可达（`10.255.129.26:6060`）
   - 检查网络连接

3. **TiviMate 无法回放**
   - 确认 M3U 中的 `catchup-source` 是否正确指向代理服务
   - 查看日志确认请求是否到达代理服务
   - 检查时间格式转换是否成功

详见 `文档/回放功能说明.md`

## 相关文档

- 回放功能详细说明：`文档/回放功能说明.md`
- 定时任务配置（Cron）：[CRON.md](./CRON.md)
