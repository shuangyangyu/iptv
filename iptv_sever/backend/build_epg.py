#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
入口脚本：生成 XMLTV（epg.xml）

用法（路由器上，无参数默认输出到 /www/iptv_sever/out/epg.xml）：
python3 /www/iptv_sever/build_epg.py
"""

from __future__ import annotations

import argparse
import os
import sys

# 允许直接跑脚本文件：把 iptv_sever 的父目录加入 sys.path
if __package__ in (None, ""):
    # 当前文件：/www/iptv_sever/backend/build_epg.py
    # 需要把 /www/ 加入 sys.path，这样就能导入 iptv_sever 包
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /www/iptv_sever/backend
    iptv_sever_dir = os.path.dirname(script_dir)  # /www/iptv_sever
    repo_root = os.path.dirname(iptv_sever_dir)  # /www/
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from iptv_sever.backend.conf import (
    DEFAULT_CHANNEL_LIST_SOURCE,
    DEFAULT_EPG_BASE_URL,
    DEFAULT_EPG_EXTRA_PARAMS,
    DEFAULT_EPG_OUT,
    DEFAULT_EPG_RIDDLE,
    DEFAULT_EPG_TIME_MS,
    DEFAULT_EPG_DAYS_BACK,
    DEFAULT_EPG_DAYS_FORWARD,
    DEFAULT_HTTP_TIMEOUT_S,
    DEFAULT_LOGO_DIR,
    DEFAULT_SOURCE_IFACE,
    DEFAULT_USER_AGENT,
    DEFAULT_WEB_BASE_URL,
    EPGSettings,
)
from iptv_sever.backend.core import load_channel_categories
from iptv_sever.backend.epg import build_xmltv, extract_epg_channels, filter_epg_by_days, indent, parse_query_params, run_epg
from iptv_sever.backend.net import build_opener, get_ipv4_from_iface, is_url


def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    作用：
    - 解析命令行参数。

    输入：
    - argv: 参数列表（不含程序名）

    输出：
    - argparse.Namespace
    """

    ap = argparse.ArgumentParser(description="生成 XMLTV epg.xml（iptv_sever）")
    ap.add_argument("--channels-url", default=DEFAULT_CHANNEL_LIST_SOURCE, help="频道列表 URL（http）")
    ap.add_argument("--out", default=DEFAULT_EPG_OUT, help="输出 epg.xml（默认 out/epg.xml）")
    ap.add_argument("--base-url", default=DEFAULT_EPG_BASE_URL, help="EPG 接口地址（POST）")
    ap.add_argument("--riddle", default=DEFAULT_EPG_RIDDLE, help="riddle（抓包参数）")
    ap.add_argument("--time", dest="time_ms", default=DEFAULT_EPG_TIME_MS, help="time（毫秒字符串，抓包参数）")
    ap.add_argument("--extra-params", default=DEFAULT_EPG_EXTRA_PARAMS, help="固定 POST 参数（querystring）")
    ap.add_argument("--timeout", type=float, default=8.0, help="单次请求超时秒数")
    ap.add_argument("--sleep", type=float, default=0.05, help="每个频道请求间隔秒数")
    ap.add_argument("--max-channels", type=int, default=0, help="限制处理频道数（0=不限制）")
    ap.add_argument("--ua", default=DEFAULT_USER_AGENT, help="User-Agent")
    ap.add_argument("--days-forward", type=int, default=DEFAULT_EPG_DAYS_FORWARD, help="向后预告天数（包含今天）")
    ap.add_argument("--days-back", type=int, default=DEFAULT_EPG_DAYS_BACK, help="向前回看天数（包含今天）")

    # 必须绑定网卡
    ap.add_argument("--source-iface", default=DEFAULT_SOURCE_IFACE, help="用于拉取频道/EPG 的网卡名（必需）")

    # icon 本地化（如果本地存在 logo 文件）
    ap.add_argument("--web-base-url", default=DEFAULT_WEB_BASE_URL, help="本地 Web Base（用于 icon src）")
    ap.add_argument("--logo-dir", default=DEFAULT_LOGO_DIR, help="logo 目录（空=自动：与 out 同目录下 logos/）")
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    """
    作用：
    - 串联 net/core/epg 生成 epg.xml。

    输入：
    - argv: 参数列表

    输出：
    - int: 退出码
    """

    args = parse_args(argv)

    # 固定默认 out 相对路径到iptv_sever根目录（/www/iptv_sever/out/epg.xml）
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /www/iptv_sever/backend
    iptv_sever_dir = os.path.dirname(script_dir)  # /www/iptv_sever
    out_arg = str(args.out)
    if out_arg == DEFAULT_EPG_OUT and not os.path.isabs(out_arg):
        # 输出到 /www/iptv_sever/out/epg.xml
        args.out = os.path.join(iptv_sever_dir, out_arg)

    settings = EPGSettings(
        channels_url=str(args.channels_url),
        out_path=str(args.out),
        base_url=str(args.base_url),
        riddle=str(args.riddle),
        time_ms=str(args.time_ms),
        extra_params_qs=str(args.extra_params),
        source_iface=str(args.source_iface),
        timeout_s=float(args.timeout),
        sleep_s=float(args.sleep),
        max_channels=int(args.max_channels),
        user_agent=str(args.ua),
        days_forward=int(args.days_forward),
        days_back=int(args.days_back),
        web_base_url=str(args.web_base_url),
        logo_dir=str(args.logo_dir),
    )

    if not is_url(settings.channels_url):
        raise SystemExit(f"--channels-url 必须是 http URL：{settings.channels_url!r}")
    if not (settings.riddle or "").strip() or not (settings.time_ms or "").strip():
        raise SystemExit("缺少 riddle/time：请在 conf.py 填写 DEFAULT_EPG_RIDDLE/DEFAULT_EPG_TIME_MS，或用命令行 --riddle/--time 覆盖")

    if not (settings.source_iface or "").strip():
        raise SystemExit("--source-iface 不能为空（必须指定用于拉取频道/EPG 的网卡）")
    bind_ip = get_ipv4_from_iface(settings.source_iface)
    if not bind_ip:
        raise SystemExit(f"无法从网卡 {settings.source_iface!r} 获取 IPv4（请确认接口 up 且 DHCP 正常）")

    opener = build_opener(bind_ip)

    # 拉取频道列表（同样走绑定网卡）
    cats = load_channel_categories(
        settings.channels_url,
        opener=opener,
        timeout_s=DEFAULT_HTTP_TIMEOUT_S,
        user_agent=settings.user_agent,
    )
    channels = extract_epg_channels(cats)

    extra_params = parse_query_params(settings.extra_params_qs)
    # 用当前出口 IP 覆盖 ip（避免写死）
    if bind_ip:
        extra_params["ip"] = bind_ip

    epg_by_channel, stats = run_epg(
        channels=channels,
        base_url=settings.base_url,
        riddle=settings.riddle,
        time_ms=settings.time_ms,
        extra_params=extra_params,
        ua=settings.user_agent,
        timeout_s=settings.timeout_s,
        opener=opener,
        sleep_s=settings.sleep_s,
        max_channels=settings.max_channels,
    )

    # 按日期范围过滤（你要的“几天预告”就在这里控制）
    epg_by_channel = filter_epg_by_days(
        epg_by_channel,
        days_back=settings.days_back,
        days_forward=settings.days_forward,
    )

    tree = build_xmltv(
        channels=channels,
        epg_by_channel=epg_by_channel,
        out_path=settings.out_path,
        logo_dir=settings.logo_dir,
        web_base_url=settings.web_base_url,
    )
    indent(tree.getroot())

    os.makedirs(os.path.dirname(settings.out_path) or ".", exist_ok=True)
    tree.write(settings.out_path, encoding="utf-8", xml_declaration=True)

    print(f"频道数：{len(channels)}")
    print(f"EPG：ok={stats.get('ok')} fail={stats.get('fail')}")
    print(f"范围：days_back={settings.days_back} days_forward={settings.days_forward}")
    print(f"输出：{settings.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


