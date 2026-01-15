#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置（conf）

你提到的“conf 文件放置常常用变量”，这里用一个独立模块来集中管理默认值，
避免把常量散落在 core/入口脚本里，后续维护会更轻松。
"""

from __future__ import annotations

from dataclasses import dataclass

# --------- 输入/输出默认值（可按你实际环境调整）---------

# 默认频道列表（channel_5.js：JSON 数组，元素包含 channelList）
DEFAULT_CHANNEL_LIST_SOURCE = "http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js"

# 默认输出文件名（建议你在命令行用 --out 明确指定；这里仅提供默认）
DEFAULT_M3U_OUT = "out/iptv.m3u"

# 默认 EPG 地址（写入 M3U 的 #EXT-X-TVG: url-tvg）
DEFAULT_X_TVG_URL = "http://192.168.1.250/iptv/epg.xml"

# udpxy（把 rtp/udp 组播地址转成 HTTP 代理地址）
DEFAULT_UDPXY_BASE = "http://192.168.1.250:4022"

# 必须绑定网卡：从网卡名取 IPv4（例如 eth1）
DEFAULT_SOURCE_IFACE = "eth1"

# HTTP 拉取超时（秒）
DEFAULT_HTTP_TIMEOUT_S = 10.0

# User-Agent：用于 urllib 请求头（有些服务端对 UA 比较敏感）
DEFAULT_USER_AGENT = "curl/8.0.0"

# --------- EPG/XMLTV（生成 epg.xml）---------

# 默认 EPG 输出文件（相对路径会在入口脚本中固定到脚本目录）
DEFAULT_EPG_OUT = "out/epg.xml"

# EPG 节目单接口（POST）
DEFAULT_EPG_BASE_URL = "http://cms.99tv.com.cn:99/cms/liveVideoOtt_searchProgramList6p1.action"

# EPG 鉴权相关参数（抓包得到）
# 说明：
# - riddle/time 往往会随时间变化；如果默认值失效，你需要用抓包/现网方式更新它们
DEFAULT_EPG_RIDDLE = "0e5172956bf2c1d87381056eb23ebe5a"
DEFAULT_EPG_TIME_MS = "1764552092957"

# 除 channelId/riddle/time/ip 外的其它固定 POST 参数（querystring 形式）
# 注意：ip 会在运行时用当前出口（source-iface）的 IPv4 覆盖
DEFAULT_EPG_EXTRA_PARAMS = (
    "platform=ZX&ums_groupid=1&areacode=01&multicast=1&mac=78%3A47%3Ae3%3A44%3Aa2%3Ab9"
    "&devicetoken=00000000-104e-0429-0186-0ff30033c587&user_paytype=0&version=4.31"
    "&boxtype=TY1608&protal=&orignal=4&nickName=itv02412432015"
    "&deviceToken=00000000-104e-0429-0186-0ff30033c587&userGroup=5"
    "&temptoken=oSutjPgM1lz60eLATln1764552073725&pageID=LookBackNewActivity_0"
    "&adType=01&clientType=ott"
)

# EPG 预告/回看范围（按“日期”过滤 programme）
# - days_forward：向后预告 N 天（包含今天）
# - days_back：向前回看 M 天（包含今天）
DEFAULT_EPG_DAYS_FORWARD = 7
DEFAULT_EPG_DAYS_BACK = 0

# --------- Logo 下载与本地化（可选）---------

# 是否下载缺失 logo（默认下载；已存在则跳过，做到“默认一键可用”）
DEFAULT_DOWNLOAD_LOGOS = True

# 是否本地化 tvg-logo（默认开启：如果本地有对应文件则改成本地 URL）
DEFAULT_LOCALIZE_LOGOS = True

# logo 下载超时（秒）
DEFAULT_LOGO_TIMEOUT_S = 10.0

# logo 下载间隔（秒）：避免过快请求
DEFAULT_LOGO_DELAY_S = 0.05

# 如果本地已存在同名文件，是否跳过下载
DEFAULT_LOGO_SKIP_EXISTING = True

# logo 保存目录：
# - 为空字符串表示“自动”：与 out_path 同目录下创建 logos/
#   例如：/www/iptv_sever/out/iptv.m3u -> /www/iptv_sever/out/logos/
# - 如需自定义，可通过 --logo-dir 覆盖
DEFAULT_LOGO_DIR = ""

# 本地访问的 Web Base（用于拼接 tvg-logo 本地 URL）
# 例如路由器：http://192.168.1.250
DEFAULT_WEB_BASE_URL = "http://192.168.1.250:8088"


@dataclass(frozen=True)
class M3USettings:
    """
    M3U 生成相关的“核心配置”。

    说明：
    - 这个 dataclass 只承载配置，不做任何逻辑处理；
    - 业务逻辑都放到 `core.py` 中，保证可测试/可复用。
    """

    # 输入：频道列表 URL（http）
    channel_source: str = DEFAULT_CHANNEL_LIST_SOURCE

    # 输出：m3u 文件路径
    out_path: str = DEFAULT_M3U_OUT

    # 将 rtp:// 或 udp:// 转换为 udpxy HTTP
    use_udpxy: bool = True
    udpxy_base: str = DEFAULT_UDPXY_BASE

    # 写入 EXT-X-TVG（播放器会用它拉 EPG）
    x_tvg_url: str = DEFAULT_X_TVG_URL

    # tvg-id 使用哪个字段（一般用 primaryid；你也可以切到 channelnumber）
    tvg_id_field: str = "primaryid"

    # URL 输入：必须绑定网卡（从网卡取 IPv4 后再 bind）
    source_iface: str = DEFAULT_SOURCE_IFACE

    # 拉取输入 URL 的超时
    timeout_s: float = DEFAULT_HTTP_TIMEOUT_S

    # 请求头 UA
    user_agent: str = DEFAULT_USER_AGENT

    # 作用：本地化 tvg-logo（默认开启）；download_logos=True 时会下载缺失文件
    localize_logos: bool = DEFAULT_LOCALIZE_LOGOS
    download_logos: bool = DEFAULT_DOWNLOAD_LOGOS
    logo_dir: str = DEFAULT_LOGO_DIR
    web_base_url: str = DEFAULT_WEB_BASE_URL
    logo_timeout_s: float = DEFAULT_LOGO_TIMEOUT_S
    logo_delay_s: float = DEFAULT_LOGO_DELAY_S
    logo_skip_existing: bool = DEFAULT_LOGO_SKIP_EXISTING


@dataclass(frozen=True)
class EPGSettings:
    """
    作用：
    - EPG/XMLTV 生成所需的核心配置（频道接口 + 节目单接口 + 鉴权参数）。

    输入：
    - 由 build_epg.py 将命令行参数打包成该配置对象

    输出：
    - 作为数据对象被 epg.py 使用
    """

    # 频道列表 URL（http）
    channels_url: str = DEFAULT_CHANNEL_LIST_SOURCE

    # 输出 XMLTV 路径
    out_path: str = DEFAULT_EPG_OUT

    # EPG 接口与鉴权参数
    base_url: str = DEFAULT_EPG_BASE_URL
    riddle: str = DEFAULT_EPG_RIDDLE
    time_ms: str = DEFAULT_EPG_TIME_MS
    extra_params_qs: str = DEFAULT_EPG_EXTRA_PARAMS

    # 网络与请求
    source_iface: str = DEFAULT_SOURCE_IFACE
    timeout_s: float = 8.0
    sleep_s: float = 0.05
    max_channels: int = 0
    user_agent: str = DEFAULT_USER_AGENT

    # 生成范围（按日期过滤）
    days_forward: int = DEFAULT_EPG_DAYS_FORWARD
    days_back: int = DEFAULT_EPG_DAYS_BACK

    # icon：优先用本地 logo（如果本地存在）
    web_base_url: str = DEFAULT_WEB_BASE_URL
    logo_dir: str = DEFAULT_LOGO_DIR


