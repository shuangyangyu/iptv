#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
核心逻辑（core）

第一阶段目标：把“直播 M3U 生成”跑通，并做到：
- 每个函数（方法）都有清晰的 docstring + 关键步骤注释
- conf.py 只放默认值/配置；core.py 只放可复用逻辑；入口脚本只负责参数解析/串联
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse
from iptv_sever.backend.net import is_url


def load_channel_categories(
    source: str,
    *,
    opener: Optional[urllib.request.OpenerDirector],
    timeout_s: float,
    user_agent: str,
) -> List[Dict]:
    """
    作用：
    - 从频道接口 URL 拉取并解析频道 JSON（channel_5.js / channel_5.pretty.json 同构）。

    输入：
    - source: 频道列表 URL（必须是 http://）
    - opener: urllib opener（可选，通常用于绑定源 IP）
    - timeout_s: 请求超时秒数
    - user_agent: HTTP User-Agent

    输出：
    - List[Dict]: root=list 的分类数组；每个元素通常包含 `channelList`
    """

    src = (source or "").strip()
    if not src:
        raise ValueError("source 不能为空")

    if not is_url(src):
        raise ValueError(f"input 必须是 URL（http）：{src!r}")

    op = opener or urllib.request.build_opener()
    req = urllib.request.Request(src, headers={"User-Agent": user_agent})
    with op.open(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("JSON 格式错误：root 应该是数组（list）")
    return data


@dataclass(frozen=True)
class Channel:
    """
    作用：
    - 承载生成 M3U 所需的最小频道字段集合。

    输入：
    - 由 `extract_channels()` 从原始 JSON 解析得到

    输出：
    - 作为数据对象被 `generate_m3u_text()` 使用
    """

    name: str
    group: str
    tvg_id: str
    tvg_name: str
    tvg_logo: str
    chno: str
    stream_url: str
    catchup_source: str = ""  # 回放URL模板（可选）


def _category_name(cat: Dict) -> str:
    """
    作用：
    - 从分类对象上取分类名（兼容不同字段名）。

    输入：
    - cat: 分类 dict

    输出：
    - str: 分类名（可能为空字符串）
    """

    for k in ("category_name", "categoryName", "name"):
        v = cat.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _iter_channel_dicts(categories: List[Dict]) -> Iterable[Tuple[str, Dict]]:
    """
    作用：
    - 把分类数组展开为 (group_name, channel_dict) 的迭代器。

    输入：
    - categories: root=list 的分类数组

    输出：
    - Iterable[(group_name, channel_dict)]: 逐条产出频道字典

    规则：
    - 若存在分类名 == “全部”：只用该分类的 channelList（避免重复）
    - 否则：遍历全部分类，把各分类 channelList 合并输出
    """

    if not categories:
        return

    # 1) 尝试找到“全部”分类（更像“全集合”）
    all_cat: Optional[Dict] = None
    for cat in categories:
        if isinstance(cat, dict) and _category_name(cat) == "全部":
            all_cat = cat
            break

    if all_cat is not None:
        group = _category_name(all_cat) or "全部"
        ch_list = all_cat.get("channelList") or []
        if isinstance(ch_list, list):
            for ch in ch_list:
                if isinstance(ch, dict):
                    yield group, ch
        return

    # 2) 没有“全部”：合并所有分类（并携带分类名作为 group-title）
    for cat in categories:
        if not isinstance(cat, dict):
            continue
        group = _category_name(cat) or ""
        ch_list = cat.get("channelList") or []
        if not isinstance(ch_list, list):
            continue
        for ch in ch_list:
            if isinstance(ch, dict):
                yield group, ch


def extract_channels(categories: List[Dict], *, tvg_id_field: str = "primaryid", web_base_url: str = "") -> Tuple[List[Channel], Optional[str], Optional[int], Optional[str]]:
    """
    作用：
    - 从频道分类数组里抽取出生成 M3U 所需的频道列表，并完成去重。
    - 同时提取回放服务器地址信息（从第一个有效的 zx 字段）

    输入：
    - categories: root=list 的分类数组（通常每个元素含 channelList）
    - tvg_id_field: tvg-id 取值字段（默认 primaryid）
    - web_base_url: Web服务器基础URL（用于构建catchup-source，例如 http://192.168.1.250:8088）

    输出：
    - Tuple[List[Channel], Optional[str], Optional[int], Optional[str]]: 
      (频道列表, catchup_host, catchup_port, virtual_domain)
    """

    out: List[Channel] = []
    seen: set[str] = set()
    
    # 用于提取回放服务器地址（只提取第一次找到的，因为所有频道通常指向同一个服务器）
    catchup_host: Optional[str] = None
    catchup_port: Optional[int] = None
    virtual_domain: Optional[str] = None

    # 作用：
    # - 生成一个“频道去重键 -> 分组名”的映射，用来解决下面这个现实问题：
    #   - 官方 channel_5.js 在“全部”分类里的 channelList，往往不带每个频道的 category_name
    #   - 但同一个频道也会出现在“央视/卫视/本地/数字/其它”等分类里，那些分类对象本身就有 category_name
    #   - 因此：我们先遍历所有“非全部”分类，建立映射；再遍历“全部”分类输出时即可反查出真实分组
    group_by_key: Dict[str, str] = {}
    for cat in categories or []:
        if not isinstance(cat, dict):
            continue
        g = _category_name(cat) or ""
        if not g or g == "全部":
            continue
        ch_list = cat.get("channelList") or []
        if not isinstance(ch_list, list):
            continue
        for ch in ch_list:
            if not isinstance(ch, dict):
                continue
            primaryid = str(ch.get("primaryid") or "").strip()
            multi_zx = str(ch.get("multi_ZX") or "").strip()
            name = str(ch.get("name") or "").strip()
            key = primaryid if primaryid else f"{name}|{multi_zx}"
            if key and key not in group_by_key:
                group_by_key[key] = g

    for group, ch in _iter_channel_dicts(categories):
        name = str(ch.get("name") or "").strip() or "未知频道"
        chno = str(ch.get("channelnumber") or "").strip()

        # tvg-id：默认用 primaryid（EPG 也通常用它）
        tvg_id = str(ch.get(tvg_id_field) or "").strip()
        if not tvg_id:
            tvg_id = str(ch.get("primaryid") or "").strip()

        # 分组名（group-title）优先级：
        # 1) 频道自身的 category_name（如果频道条目带这个字段，最准确）
        # 2) 从其它分类反查（解决“全部分类里没带 category_name”的情况）
        # 3) 最后才回退到当前分类名 group（可能是“全部”）
        primaryid = str(ch.get("primaryid") or "").strip()
        multi_zx = str(ch.get("multi_ZX") or "").strip()
        lookup_key = primaryid if primaryid else f"{name}|{multi_zx}"
        group_title = (
            str(ch.get("category_name") or "").strip()
            or group_by_key.get(lookup_key, "")
            or group
        )

        # logo：频道图标 url
        logo = str(ch.get("fileurl") or "").strip()

        # 直播源：组播地址（rtp://...）
        multi_zx = str(ch.get("multi_ZX") or "").strip()
        if not multi_zx:
            # 第一阶段：没有直播地址就先跳过（避免输出不可播条目）
            continue

        # 提取回放信息（从 zx 字段）
        catchup_source = ""
        zx = str(ch.get("zx") or "").strip()
        if zx:
            try:
                parsed = urlparse(zx)
                catchup_path = parsed.path.lstrip('/')  # 去掉开头的 /
                
                # 提取服务器地址（只提取第一次找到的）
                if not catchup_host and parsed.hostname and parsed.port:
                    catchup_host = parsed.hostname
                    catchup_port = parsed.port
                    
                    # 提取 virtualDomain（如果有）
                    query_params = parse_qs(parsed.query)
                    if 'virtualDomain' in query_params:
                        virtual_domain = query_params['virtualDomain'][0]
                
                # 构建代理服务器的 catchup-source 模板（只有当 web_base_url 存在时）
                if catchup_path and web_base_url:
                    # 格式：http://{web_base_url}/catchup/{catchup_path}?programbegin={start}&programend={end}
                    catchup_source = f"{web_base_url.rstrip('/')}/catchup/{catchup_path}?programbegin={{start}}&programend={{end}}"
            except Exception:
                pass  # 如果解析失败，catchup_source 保持为空

        dedup_key = tvg_id if tvg_id else f"{name}|{multi_zx}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        out.append(
            Channel(
                name=name,
                group=group_title,
                tvg_id=tvg_id,
                tvg_name=name,
                tvg_logo=logo,
                chno=chno,
                stream_url=multi_zx,
                catchup_source=catchup_source,
            )
        )

    return out, catchup_host, catchup_port, virtual_domain


def convert_multicast_to_udpxy(stream_url: str, udpxy_base: str) -> str:
    """
    作用：
    - 将 rtp:// 或 udp:// 的组播地址转换为 udpxy 的 HTTP 代理地址。

    输入：
    - stream_url: 原始播放地址（rtp://... 或 udp://...）
    - udpxy_base: udpxy base（例如 http://192.168.1.250:4022）

    输出：
    - str: 转换后的 HTTP 地址；如果不匹配则原样返回
    """

    u = (stream_url or "").strip()
    base = (udpxy_base or "").strip().rstrip("/")
    if not u or not base:
        return u

    if u.startswith("rtp://"):
        addr = u[len("rtp://") :].split("?")[0]
        return f"{base}/rtp/{addr}"
    if u.startswith("udp://"):
        addr = u[len("udp://") :].split("?")[0]
        return f"{base}/udp/{addr}"
    return u


def _escape_attr(v: str) -> str:
    """
    作用：
    - 转义 M3U EXTINF 属性值中的双引号。

    输入：
    - v: 属性值

    输出：
    - str: 转义后的属性值
    """

    return (v or "").replace('"', '\\"')


def build_extinf(ch: Channel) -> str:
    """
    作用：
    - 生成一条 EXTINF 行（不含播放地址那一行）。

    输入：
    - ch: Channel 频道对象

    输出：
    - str: EXTINF 行文本
    """

    parts = ["#EXTINF:-1"]

    # 添加 catchup 配置（如果有）
    if ch.catchup_source:
        # 使用 default 模式，只支持 TiviMate
        parts.append('catchup="default"')
        parts.append(f'catchup-source="{_escape_attr(ch.catchup_source)}"')

    if ch.tvg_id:
        parts.append(f'tvg-id="{_escape_attr(ch.tvg_id)}"')
    if ch.tvg_name:
        parts.append(f'tvg-name="{_escape_attr(ch.tvg_name)}"')
    if ch.tvg_logo:
        parts.append(f'tvg-logo="{_escape_attr(ch.tvg_logo)}"')
    if ch.group:
        parts.append(f'group-title="{_escape_attr(ch.group)}"')
    if ch.chno:
        # 非标准字段：部分播放器会用它排序/显示频道号
        parts.append(f'tvg-chno="{_escape_attr(ch.chno)}"')

    # 逗号后面是"显示名"
    return " ".join(parts) + f",{ch.name}"


def generate_m3u_text(
    channels: List[Channel],
    *,
    x_tvg_url: str = "",
) -> str:
    """
    作用：
    - 生成完整的 M3U 文本内容。

    输入：
    - channels: 频道列表
    - x_tvg_url: EPG 地址（可选；会写入 #EXT-X-TVG url-tvg）

    输出：
    - str: M3U 文本（以 \\n 结尾）
    """

    lines: List[str] = ["#EXTM3U"]

    xtvg = (x_tvg_url or "").strip()
    if xtvg:
        lines.append(f'#EXT-X-TVG url-tvg="{_escape_attr(xtvg)}"')

    for ch in channels:
        lines.append(build_extinf(ch))
        lines.append(ch.stream_url)

    return "\n".join(lines) + "\n"


def write_text(path: str, text: str) -> None:
    """
    作用：
    - 把文本写入到文件（自动创建父目录）。

    输入：
    - path: 输出文件路径
    - text: 要写入的内容

    输出：
    - None（副作用：写文件；UTF-8 编码）
    """

    p = (path or "").strip()
    if not p:
        raise ValueError("输出路径不能为空")

    parent = os.path.dirname(p)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


