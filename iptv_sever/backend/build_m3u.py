#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
入口脚本：生成直播 M3U（第一步）

特点：
- 不考虑 OpenWrt（纯本机运行）
- 参数尽量直观：input/out/udpxy/x-tvg-url
- 逻辑都在 core.py；这里负责“把参数转成配置，然后调用 core”

用法示例（URL 输入）：
python3 iptv_sever/build_m3u.py \
  --input 'http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js' \
  --out   /Users/yushuangyang/Documents/dev/iptv/out/iptv_from_iptv_sever.m3u
"""

from __future__ import annotations

import argparse
import sys
import os

# 允许两种运行方式：
# 1) 在仓库根目录：python3 -m iptv_sever.backend.build_m3u ...
# 2) 直接跑脚本文件：python3 iptv_sever/backend/build_m3u.py ...
#
# 第二种情况下，Python 默认不会把"仓库根目录"加入 sys.path，导致 `import iptv_sever.backend` 失败。
# 这里做一个最小自举：把 iptv_sever 的父目录插入到 sys.path。
if __package__ in (None, ""):
    # 当前文件：/www/iptv_sever/backend/build_m3u.py
    # 需要把 /www/ 加入 sys.path，这样就能导入 iptv_sever 包
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /www/iptv_sever/backend
    iptv_sever_dir = os.path.dirname(script_dir)  # /www/iptv_sever
    repo_root = os.path.dirname(iptv_sever_dir)  # /www/
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from iptv_sever.backend.conf import (
    DEFAULT_CHANNEL_LIST_SOURCE,
    DEFAULT_HTTP_TIMEOUT_S,
    DEFAULT_DOWNLOAD_LOGOS,
    DEFAULT_LOGO_DELAY_S,
    DEFAULT_LOGO_DIR,
    DEFAULT_LOGO_SKIP_EXISTING,
    DEFAULT_LOGO_TIMEOUT_S,
    DEFAULT_LOCALIZE_LOGOS,
    DEFAULT_M3U_OUT,
    DEFAULT_SOURCE_IFACE,
    DEFAULT_UDPXY_BASE,
    DEFAULT_USER_AGENT,
    DEFAULT_WEB_BASE_URL,
    DEFAULT_X_TVG_URL,
    M3USettings,
)
from iptv_sever.backend.core import (
    Channel,
    convert_multicast_to_udpxy,
    extract_channels,
    generate_m3u_text,
    load_channel_categories,
    write_text,
)
from iptv_sever.backend.logo import localize_logos
from iptv_sever.backend.net import build_opener, get_ipv4_from_iface, is_url


def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    作用：
    - 解析命令行参数（单独封装，便于后续扩展/测试）。

    输入：
    - argv: 命令行参数列表（不含程序名）

    输出：
    - argparse.Namespace: 解析后的参数对象
    """

    ap = argparse.ArgumentParser(description="生成直播 M3U（iptv_sever 第一阶段）")
    ap.add_argument("--input", default=DEFAULT_CHANNEL_LIST_SOURCE, help="频道列表 URL（http，默认官方 channel_5.js）")
    ap.add_argument("--out", default=DEFAULT_M3U_OUT, help="输出 m3u 路径（默认 out/iptv.m3u）")

    ap.add_argument("--udpxy", default=DEFAULT_UDPXY_BASE, help="udpxy base（例如 http://192.168.1.250:4022）")
    ap.add_argument("--no-udpxy", action="store_true", help="不做 rtp/udp → udpxy 转换（直接输出 multi_ZX）")

    ap.add_argument("--x-tvg-url", default=DEFAULT_X_TVG_URL, help='写入 M3U 的 EPG 地址（#EXT-X-TVG url-tvg="..."）')
    ap.add_argument("--tvg-id-field", default="primaryid", choices=["primaryid", "channelnumber"], help="tvg-id 取值字段（默认 primaryid）")

    ap.add_argument("--timeout", type=float, default=DEFAULT_HTTP_TIMEOUT_S, help="拉取输入 URL 的超时秒数（默认 10）")
    ap.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="拉取输入 URL 的 User-Agent（默认 curl/8.0.0）")

    # URL 输入：必须绑定网卡（从该网卡取 IPv4）
    ap.add_argument("--source-iface", default=DEFAULT_SOURCE_IFACE, help="用于拉取频道 URL 的网卡名（必需；会从该网卡取 IPv4 并 bind）")

    # Logo：下载并改成本地 URL（可选）
    ap.add_argument("--download-logos", action="store_true", default=DEFAULT_DOWNLOAD_LOGOS, help="下载 logo 并把 tvg-logo 改成本地 URL")
    ap.add_argument("--no-download-logos", action="store_true", help="不下载 logo（保持 tvg-logo 为原始 URL）")
    ap.add_argument(
        "--localize-logos",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_LOCALIZE_LOGOS,
        help="是否本地化 tvg-logo（默认开启：本地有文件则改 URL）",
    )
    ap.add_argument("--logo-dir", default=DEFAULT_LOGO_DIR, help="logo 保存目录（空=自动：与 out 同目录下 logos/）")
    ap.add_argument("--web-base-url", default=DEFAULT_WEB_BASE_URL, help="本地 Web Base（用于拼接 logo URL，例如 http://192.168.1.250）")
    ap.add_argument("--logo-timeout", type=float, default=DEFAULT_LOGO_TIMEOUT_S, help="下载 logo 超时秒数")
    ap.add_argument("--logo-delay", type=float, default=DEFAULT_LOGO_DELAY_S, help="下载 logo 间隔秒数")
    ap.add_argument(
        "--logo-skip-existing",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_LOGO_SKIP_EXISTING,
        help="本地已存在同名 logo 时是否跳过下载（默认跳过）",
    )
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    """
    作用：
    - 串联 net/core 完成：拉取频道 → 抽取频道 → 生成 M3U → 写文件。

    输入：
    - argv: 命令行参数列表（不含程序名）

    输出：
    - int: 进程退出码（0 表示成功）
    """

    args = parse_args(argv)

    # 把默认的相对路径（out/iptv.m3u）固定到"iptv_sever根目录/out"，而不是backend/out
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /www/iptv_sever/backend
    iptv_sever_dir = os.path.dirname(script_dir)  # /www/iptv_sever
    out_arg = str(args.out)
    if out_arg == DEFAULT_M3U_OUT and not os.path.isabs(out_arg):
        # 输出到 /www/iptv_sever/out/iptv.m3u
        args.out = os.path.join(iptv_sever_dir, out_arg)

    # 1) 组装 Settings（conf.py 中定义的“配置结构”）
    settings = M3USettings(
        channel_source=str(args.input),
        out_path=str(args.out),
        use_udpxy=(not bool(args.no_udpxy)),
        udpxy_base=str(args.udpxy),
        x_tvg_url=str(args.x_tvg_url),
        tvg_id_field=str(args.tvg_id_field),
        source_iface=str(args.source_iface),
        timeout_s=float(args.timeout),
        user_agent=str(args.user_agent),
        localize_logos=bool(args.localize_logos),
        download_logos=(bool(args.download_logos) and (not bool(args.no_download_logos))),
        logo_dir=str(args.logo_dir),
        web_base_url=str(args.web_base_url),
        logo_timeout_s=float(args.logo_timeout),
        logo_delay_s=float(args.logo_delay),
        logo_skip_existing=bool(args.logo_skip_existing),
    )

    # 2) 强制 URL 输入（你明确说最终一定是 URL）
    if not is_url(settings.channel_source):
        raise SystemExit(f"--input 必须是 URL（http），当前为：{settings.channel_source!r}")

    # 3) 必须绑定网卡：从网卡取 IPv4，并用于 bind
    if not (settings.source_iface or "").strip():
        raise SystemExit("--source-iface 不能为空（必须指定用于拉取频道 URL 的网卡）")

    bind_ip = get_ipv4_from_iface(settings.source_iface)
    if not bind_ip:
        raise SystemExit(f"无法从网卡 {settings.source_iface!r} 获取 IPv4（请确认网卡 up 且已拿到 DHCP）")

    opener = build_opener(bind_ip)

    # 3) 加载 JSON 并抽取频道
    categories = load_channel_categories(
        settings.channel_source,
        opener=opener,
        timeout_s=settings.timeout_s,
        user_agent=settings.user_agent,
    )
    channels, catchup_host, catchup_port, virtual_domain = extract_channels(
        categories, 
        tvg_id_field=settings.tvg_id_field,
        web_base_url=settings.web_base_url
    )
    # 注意：这里提取的 catchup_host/port/domain 暂时不使用
    # 因为 build_m3u.py 是独立脚本，不直接修改配置
    # 地址信息会在 execute_job() 中提取并保存

    # 4) Logo：默认“只改地址”，显式 --download-logos 才下载缺失
    if settings.localize_logos:
        channels, stats = localize_logos(
            channels,
            out_path=settings.out_path,
            logo_dir=settings.logo_dir,
            web_base_url=settings.web_base_url,
            opener=opener,
            timeout_s=settings.logo_timeout_s,
            delay_s=settings.logo_delay_s,
            skip_existing=settings.logo_skip_existing,
            download_missing=settings.download_logos,
            user_agent=settings.user_agent,
        )

    # 4) 地址处理：可选转换成 udpxy HTTP
    if settings.use_udpxy:
        channels = [
            Channel(
                name=ch.name,
                group=ch.group,
                tvg_id=ch.tvg_id,
                tvg_name=ch.tvg_name,
                tvg_logo=ch.tvg_logo,
                chno=ch.chno,
                stream_url=convert_multicast_to_udpxy(ch.stream_url, settings.udpxy_base),
                catchup_source=ch.catchup_source,  # 保留 catchup_source
            )
            for ch in channels
        ]

    # 5) 输出 M3U
    m3u_text = generate_m3u_text(channels, x_tvg_url=settings.x_tvg_url)
    write_text(settings.out_path, m3u_text)

    print(f"读取：{settings.channel_source}")
    print(f"频道数：{len(channels)}")
    print(f"输出：{settings.out_path}")
    if settings.localize_logos:
        print(
            "logo："
            f"downloaded={stats.get('downloaded')} "
            f"skipped={stats.get('skipped')} "
            f"failed={stats.get('failed')} "
            f"missing={stats.get('missing')} "
            f"rewritten={stats.get('rewritten')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


