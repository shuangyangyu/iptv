#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logo 下载与本地化（logo）

职责：
- 下载频道 logo 到本地目录
- 把 tvg-logo 重写成可访问的本地 URL
"""

from __future__ import annotations

import os
import time
import urllib.request
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from iptv_sever.backend.core import Channel


def _safe_filename(name: str) -> str:
    """
    作用：
    - 生成一个适合作为文件名的字符串（最小清洗）。

    输入：
    - name: 原始字符串

    输出：
    - str: 清洗后的文件名（不包含路径分隔符）
    """

    x = (name or "").strip()
    x = x.replace("/", "_").replace("\\", "_").replace("\x00", "")
    return x or "logo"


def logo_filename_from_url(logo_url: str, *, fallback_stem: str) -> str:
    """
    作用：
    - 从 logo URL 中提取文件名（用于本地落盘）。

    输入：
    - logo_url: 形如 http://.../xxx.png 或 http://.../xxx.jpg
    - fallback_stem: URL 中无法取到文件名时使用的兜底（例如 primaryid）

    输出：
    - str: 文件名（包含扩展名，尽量保留原扩展名）
    """

    u = (logo_url or "").strip()
    stem = _safe_filename(fallback_stem)
    if not u:
        return stem + ".png"

    # 直接从路径末尾取 basename
    base = u.split("?", 1)[0].rstrip("/").split("/")[-1].strip()
    base = _safe_filename(base)
    if not base or base == "logo":
        return stem + ".png"

    # 如果没有扩展名，给一个默认 .png
    if "." not in base:
        return base + ".png"
    return base


def _www_path_to_url_path(p: str) -> str:
    """
    作用：
    - 把 /www/... 这种文件系统路径映射成 Web 路径 /...（常见于 OpenWrt/uhttpd）。

    输入：
    - p: 文件系统路径，例如 /www/iptv_sever/out/logos

    输出：
    - str: Web 路径，例如 /iptv_sever/out/logos
    """

    x = (p or "").strip()
    if x.startswith("/www/"):
        return "/" + x[len("/www/") :].lstrip("/")
    return x


def download_logo(
    logo_url: str,
    *,
    save_path: str,
    opener: Optional[urllib.request.OpenerDirector],
    timeout_s: float,
    user_agent: str,
) -> bool:
    """
    作用：
    - 下载单个 logo 到指定路径。

    输入：
    - logo_url: logo 的 http URL
    - save_path: 本地保存路径（完整路径）
    - opener: urllib opener（可选）
    - timeout_s: 超时秒数
    - user_agent: 请求 UA

    输出：
    - bool: 下载成功 True，否则 False
    """

    u = (logo_url or "").strip()
    if not u:
        return False

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    op = opener or urllib.request.build_opener()
    req = urllib.request.Request(u, headers={"User-Agent": user_agent})
    try:
        with op.open(req, timeout=timeout_s) as resp:
            data = resp.read()
        with open(save_path, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


def localize_logos(
    channels: List["Channel"],
    *,
    out_path: str,
    logo_dir: str,
    web_base_url: str,
    opener: Optional[urllib.request.OpenerDirector],
    timeout_s: float,
    delay_s: float,
    skip_existing: bool,
    download_missing: bool,
    user_agent: str,
) -> Tuple[List["Channel"], Dict[str, int]]:
    """
    作用：
    - 下载频道 logo 到本地目录，并把每个 Channel.tvg_logo 重写为本地可访问 URL。

    输入：
    - channels: 频道列表
    - out_path: m3u 输出路径（用于自动推导 logo_dir）
    - logo_dir: logo 目录；为空表示自动使用“out_path 同目录下 logos/”
    - web_base_url: Web 基础地址（例如 http://192.168.1.250）
    - opener/timeout_s/user_agent: 下载用的请求参数
    - delay_s: 两次下载之间 sleep 秒数
    - skip_existing: 已存在同名文件时是否跳过下载
    - download_missing: 本地缺失时是否下载（False=只重写不下载）

    输出：
    - (new_channels, stats):
      - new_channels: tvg_logo 已替换成本地 URL 的频道列表
      - stats: 统计信息（downloaded/skipped/failed/rewritten）
    """

    from iptv_sever.backend.core import Channel  # 避免循环 import（仅在运行时需要）

    # 自动推导 logo_dir：与 out_path 同目录，但确保在 out/ 目录下
    ldir = (logo_dir or "").strip()
    if not ldir:
        # logo_dir 为空，自动推导
        out_dir = os.path.dirname(out_path) or "."
        # 检查 out_path 的父目录名是否是 "out"
        out_dir_name = os.path.basename(out_dir)
        if out_dir_name == "out":
            # 如果输出目录已经是 out/，直接使用同目录下的 logos/
            ldir = os.path.join(out_dir, "logos")
        else:
            # 如果输出目录不是 out/，强制使用 out/logos/
            # 获取 out_path 所在的基础目录（通常是 /www/iptv_sever）
            base_dir = os.path.dirname(out_path) or "."
            ldir = os.path.join(base_dir, "out", "logos")
    else:
        # logo_dir 不为空，但需要确保在 out/ 目录下
        # 如果传入的路径不在 out/ 目录下，强制转换
        ldir_abs = os.path.abspath(ldir)
        out_dir_abs = os.path.dirname(os.path.abspath(out_path)) or "."
        # 检查 logo_dir 是否在 out/ 目录下
        if "out" not in ldir_abs.split(os.sep) or os.path.basename(os.path.dirname(ldir_abs)) != "out":
            # 如果不在 out/ 目录下，强制使用 out/logos/
            base_dir = os.path.dirname(os.path.abspath(out_path)) or "."
            # 如果 out_path 已经在 out/ 目录下，使用 out/logos/
            if os.path.basename(base_dir) == "out":
                ldir = os.path.join(base_dir, "logos")
            else:
                # 如果 out_path 不在 out/ 目录下，使用 base_dir/out/logos/
                ldir = os.path.join(base_dir, "out", "logos")

    # 本地 URL 前缀：web_base_url + 映射后的路径
    # 确保路径以 /out/ 开头（Flask 路由是 /out/<path:filename>）
    base = (web_base_url or "").rstrip("/")
    # 从 logo_dir 中提取 /out/logos 部分
    ldir_str = str(ldir)
    # 查找 /out/logos 在路径中的位置
    out_logos_idx = ldir_str.find("/out/logos")
    if out_logos_idx >= 0:
        # 直接使用 /out/logos 作为 URL 路径
        url_path = "/out/logos"
    else:
        # 回退到原来的逻辑
        url_path = _www_path_to_url_path(ldir)
    url_prefix = base + url_path
    url_prefix = url_prefix.rstrip("/")

    stats = {"downloaded": 0, "skipped": 0, "failed": 0, "rewritten": 0, "missing": 0}
    new_list: List[Channel] = []

    for ch in channels:
        logo = (ch.tvg_logo or "").strip()
        if not logo:
            new_list.append(ch)
            continue

        # 用 tvg_id 做 fallback（更稳定）；没有则用 name
        fn = logo_filename_from_url(logo, fallback_stem=ch.tvg_id or ch.name)
        save_path = os.path.join(ldir, fn)

        if os.path.exists(save_path) and os.path.getsize(save_path) > 0 and skip_existing:
            stats["skipped"] += 1
        elif os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            # 文件已存在但不跳过：允许后续 download_missing=True 时覆盖下载
            pass
        elif not download_missing:
            # 默认模式：不下载，只在本地有文件时才改 URL
            stats["missing"] += 1
        else:
            ok = download_logo(
                logo,
                save_path=save_path,
                opener=opener,
                timeout_s=timeout_s,
                user_agent=user_agent,
            )
            if ok:
                stats["downloaded"] += 1
            else:
                stats["failed"] += 1

            if delay_s and delay_s > 0:
                time.sleep(float(delay_s))

        # 只要本地文件存在，就改成本地 URL；否则保留原 logo
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            local_url = f"{url_prefix}/{fn}"
            stats["rewritten"] += 1
            new_list.append(
                Channel(
                    name=ch.name,
                    group=ch.group,
                    tvg_id=ch.tvg_id,
                    tvg_name=ch.tvg_name,
                    tvg_logo=local_url,
                    chno=ch.chno,
                    stream_url=ch.stream_url,
                    catchup_source=ch.catchup_source,  # 保留 catchup_source
                )
            )
        else:
            new_list.append(ch)

    return new_list, stats


