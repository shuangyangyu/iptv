#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EPG/XMLTV 生成核心逻辑（epg）

职责：
- 调用 EPG 节目单接口（POST）抓取每个频道的节目列表
- 生成标准 XMLTV（epg.xml）
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from iptv_sever.backend.logo import logo_filename_from_url

TZ_CN = dt.timezone(dt.timedelta(hours=8))

def _date_key_to_date(s: str) -> Optional[dt.date]:
    """
    作用：
    - 把 YYYYMMDD 的 date_key 转为 date。

    输入：
    - s: YYYYMMDD 字符串

    输出：
    - date 或 None（格式非法）
    """

    x = (s or "").strip()
    if len(x) != 8 or not x.isdigit():
        return None
    try:
        return dt.date(int(x[0:4]), int(x[4:6]), int(x[6:8]))
    except Exception:
        return None


def filter_epg_by_days(
    epg_by_channel: Dict[str, Dict[str, Any]],
    *,
    days_back: int,
    days_forward: int,
    now: Optional[dt.datetime] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    作用：
    - 按“日期范围”过滤 EPG JSON，只保留指定天数内的数据。

    输入：
    - epg_by_channel: {channelId: {YYYYMMDD: [items...]}}
    - days_back: 向前保留天数（包含今天）
    - days_forward: 向后保留天数（包含今天）
    - now: 当前时间（可选，默认取现在；按中国时区计算日期）

    输出：
    - Dict[str, Dict[str, Any]]: 过滤后的 EPG JSON（结构同输入）
    """

    nb = int(days_back)
    nf = int(days_forward)
    if nb < 0:
        nb = 0
    if nf < 0:
        nf = 0

    now_dt = (now or dt.datetime.now(tz=TZ_CN)).astimezone(TZ_CN)
    today = now_dt.date()
    start_d = today - dt.timedelta(days=nb)
    end_d = today + dt.timedelta(days=nf)

    out: Dict[str, Dict[str, Any]] = {}
    for cid, data in (epg_by_channel or {}).items():
        if not isinstance(data, dict):
            continue
        keep: Dict[str, Any] = {}
        for date_key, items in data.items():
            d = _date_key_to_date(str(date_key))
            if d is None:
                continue
            if start_d <= d <= end_d:
                keep[str(date_key)] = items
        if keep:
            out[str(cid)] = keep
    return out


def parse_query_params(qs: str) -> Dict[str, str]:
    """
    作用：
    - 把 a=b&c=d 形式的 querystring 解析成 dict（重复 key 以最后一个为准）。

    输入：
    - qs: querystring 字符串

    输出：
    - Dict[str, str]: 参数字典
    """

    out: Dict[str, str] = {}
    for k, v in urllib.parse.parse_qsl(qs or "", keep_blank_values=True):
        if not k:
            continue
        out[str(k)] = str(v)
    return out


def xmltv_ts(d: dt.datetime) -> str:
    """
    作用：
    - 将 datetime 转换为 XMLTV 时间格式：YYYYMMDDHHMMSS +0800

    输入：
    - d: datetime（可无 tzinfo）

    输出：
    - str: XMLTV 时间字符串
    """

    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ_CN)
    d = d.astimezone(TZ_CN)
    return d.strftime("%Y%m%d%H%M%S %z")


def parse_hhmm(s: str) -> Tuple[int, int, int]:
    """
    作用：
    - 解析 HH:MM 或 HH:MM:SS 时间字符串。

    输入：
    - s: 时间字符串

    输出：
    - (hh, mm, ss)
    """

    x = (s or "").strip()
    parts = x.split(":")
    if len(parts) == 2:
        hh, mm = parts
        return int(hh), int(mm), 0
    if len(parts) == 3:
        hh, mm, ss = parts
        return int(hh), int(mm), int(ss)
    raise ValueError(f"invalid time: {s!r}")


def parse_duration_hhmmss(s: str) -> dt.timedelta:
    """
    作用：
    - 解析 duration=HHMMSS（6 位数字）为 timedelta。

    输入：
    - s: 6 位数字字符串

    输出：
    - timedelta
    """

    x = (s or "").strip()
    if len(x) != 6 or not x.isdigit():
        raise ValueError(f"invalid duration: {s!r}")
    hh = int(x[0:2])
    mm = int(x[2:4])
    ss = int(x[4:6])
    return dt.timedelta(hours=hh, minutes=mm, seconds=ss)


def compute_stop(start: dt.datetime, item: Dict[str, Any]) -> Optional[dt.datetime]:
    """
    作用：
    - 根据节目条目计算 stop 时间（优先 duration，其次 endTime）。

    输入：
    - start: 开始时间（带 tzinfo）
    - item: 节目条目 dict（来自 EPG JSON）

    输出：
    - datetime | None
    """

    dur = item.get("duration")
    if dur:
        try:
            return start + parse_duration_hhmmss(str(dur))
        except Exception:
            pass

    end_time = item.get("endTime")
    if end_time:
        try:
            hh, mm, ss = parse_hhmm(str(end_time))
            end_dt = start.replace(hour=hh, minute=mm, second=ss)
            if end_dt <= start:
                end_dt = end_dt + dt.timedelta(days=1)
            return end_dt
        except Exception:
            pass
    return None


def fetch_program_list(
    *,
    base_url: str,
    channel_id: str,
    riddle: str,
    time_ms: str,
    extra_params: Dict[str, str],
    ua: str,
    timeout_s: float,
    opener: Optional[urllib.request.OpenerDirector],
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    作用：
    - 调用 EPG 接口获取单个频道的节目列表（返回 JSON dict）。

    输入：
    - base_url: EPG 接口地址（POST）
    - channel_id: 频道 primaryid
    - riddle/time_ms: 抓包参数
    - extra_params: 额外固定参数 dict（会自动覆盖 channelId/riddle/time）
    - ua/timeout_s/opener: 请求参数

    输出：
    - (data, meta):
      - data: JSON dict（成功）或 None（失败）
      - meta: Content-Type 或错误信息（便于排查）
    """

    params: Dict[str, str] = dict(extra_params or {})
    params["channelId"] = str(channel_id)
    params["riddle"] = str(riddle)
    params["time"] = str(time_ms)

    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        base_url,
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": ua,
        },
    )

    try:
        op = opener or urllib.request.build_opener()
        with op.open(req, timeout=timeout_s) as resp:
            ctype = resp.headers.get("Content-Type", "") or ""
            payload = resp.read()
            text = payload.decode("utf-8", errors="replace")
            if "application/json" in ctype.lower():
                return json.loads(text), ctype
            return None, ctype
    except urllib.error.HTTPError as e:
        try:
            body_txt = e.read().decode("utf-8", errors="replace")
        except Exception:
            body_txt = ""
        return None, f"HTTPError {e.code} {e.reason} body={body_txt[:120]!r}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _www_path_to_url_path(p: str) -> str:
    x = (p or "").strip()
    if x.startswith("/www/"):
        return "/" + x[len("/www/") :].lstrip("/")
    return x


def local_icon_src(
    icon_url: str,
    *,
    channel_id: str,
    out_path: str,
    logo_dir: str,
    web_base_url: str,
) -> str:
    """
    作用：
    - 给 XMLTV 的 <icon src="..."> 生成 URL：优先命中本地 logo，否则回退原始 icon_url。

    输入：
    - icon_url: 频道原始 icon URL
    - channel_id: primaryid（用于兜底文件名）
    - out_path: epg.xml 输出路径（用于自动推导 logo_dir）
    - logo_dir: logo 保存目录（空=自动：与 out_path 同目录下 logos/）
    - web_base_url: 路由器 Web base（例如 http://192.168.1.250）

    输出：
    - str: icon src URL
    """

    url = (icon_url or "").strip()
    if not url:
        return url

    ldir = (logo_dir or "").strip()
    import os

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

    fn = logo_filename_from_url(url, fallback_stem=channel_id)
    local_path = os.path.join(ldir, fn)
    if not (os.path.exists(local_path) and os.path.getsize(local_path) > 0):
        return url

    base = (web_base_url or "").rstrip("/")
    # 确保路径以 /out/logos 开头（Flask 路由是 /out/<path:filename>）
    ldir_str = str(ldir)
    # 查找 /out/logos 在路径中的位置
    out_logos_idx = ldir_str.find("/out/logos")
    if out_logos_idx >= 0:
        # 直接使用 /out/logos 作为 URL 路径
        web_dir = "/out/logos"
    else:
        # 回退到原来的逻辑
        web_dir = _www_path_to_url_path(ldir).rstrip("/")
    return f"{base}{web_dir}/{fn}" if base else f"{web_dir}/{fn}"


def extract_epg_channels(categories: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    作用：
    - 从 channel_5.js 的分类数组中抽取 EPG 需要的频道列表（id/name/icon）。

    输入：
    - categories: root=list 的分类数组

    输出：
    - List[Dict[str,str]]: [{"id":..., "name":..., "icon":...}, ...]
    """

    channels: List[Dict[str, str]] = []
    seen: set[str] = set()
    for cat in categories or []:
        if not isinstance(cat, dict):
            continue
        for ch in cat.get("channelList", []) or []:
            if not isinstance(ch, dict):
                continue
            cid = ch.get("primaryid")
            if cid is None:
                continue
            cid_s = str(cid).strip()
            if not cid_s or cid_s in seen:
                continue
            seen.add(cid_s)
            channels.append(
                {
                    "id": cid_s,
                    "name": str(ch.get("name") or cid_s),
                    "icon": str(ch.get("fileurl") or ch.get("titleurl") or ""),
                }
            )
    return channels


def build_xmltv(
    *,
    channels: List[Dict[str, str]],
    epg_by_channel: Dict[str, Dict[str, Any]],
    out_path: str,
    logo_dir: str,
    web_base_url: str,
) -> ET.ElementTree:
    """
    作用：
    - 构建 XMLTV 的 ElementTree（tv/channel/programme）。

    输入：
    - channels: 频道列表（id/name/icon）
    - epg_by_channel: 每个频道的节目 JSON（按日期分组）
    - out_path/logo_dir/web_base_url: 用于 icon 本地化

    输出：
    - ElementTree: 可直接 write() 成 epg.xml
    """

    tv = ET.Element(
        "tv",
        {
            "generator-info-name": "iptv_sever-xmltv",
            "source-info-name": "cms.99tv.com.cn",
            "source-info-url": "http://cms.99tv.com.cn:99/",
        },
    )

    for ch in channels:
        ce = ET.SubElement(tv, "channel", {"id": ch["id"]})
        dn = ET.SubElement(ce, "display-name")
        dn.text = str(ch.get("name") or ch["id"])
        icon = (ch.get("icon") or "").strip()
        if icon:
            src = local_icon_src(
                icon,
                channel_id=ch["id"],
                out_path=out_path,
                logo_dir=logo_dir,
                web_base_url=web_base_url,
            )
            ET.SubElement(ce, "icon", {"src": src})

    for cid, data in (epg_by_channel or {}).items():
        for date_key, items in (data or {}).items():
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                program_name = (it.get("programName") or "").strip()
                if not program_name:
                    continue

                start_date = (it.get("startDate") or date_key or "").strip()
                start_time = (it.get("startTime") or "").strip()
                if not (start_date and start_time):
                    continue

                try:
                    y = int(start_date[0:4])
                    m = int(start_date[4:6])
                    d = int(start_date[6:8])
                    hh, mm, ss = parse_hhmm(start_time)
                    start_dt = dt.datetime(y, m, d, hh, mm, ss, tzinfo=TZ_CN)
                except Exception:
                    continue

                stop_dt = compute_stop(start_dt, it)
                attrs = {"channel": cid, "start": xmltv_ts(start_dt)}
                if stop_dt is not None:
                    attrs["stop"] = xmltv_ts(stop_dt)
                pe = ET.SubElement(tv, "programme", attrs)
                title = ET.SubElement(pe, "title", {"lang": "zh"})
                title.text = program_name

    return ET.ElementTree(tv)


def indent(elem: ET.Element, level: int = 0) -> None:
    """
    作用：
    - 对 ElementTree 做缩进美化（Python 3.8 兼容）。

    输入：
    - elem: 根元素
    - level: 缩进层级

    输出：
    - None（原地修改 elem）
    """

    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def run_epg(
    *,
    channels: List[Dict[str, str]],
    base_url: str,
    riddle: str,
    time_ms: str,
    extra_params: Dict[str, str],
    ua: str,
    timeout_s: float,
    opener: Optional[urllib.request.OpenerDirector],
    sleep_s: float,
    max_channels: int,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
    """
    作用：
    - 批量抓取频道节目单（EPG JSON）。

    输入：
    - channels: 频道列表
    - base_url/riddle/time_ms/extra_params: EPG 请求参数
    - ua/timeout_s/opener: 请求参数
    - sleep_s: 每个频道请求间隔
    - max_channels: 0=不限制

    输出：
    - (epg_by_channel, stats)
    """

    epg_by_channel: Dict[str, Dict[str, Any]] = {}
    stats = {"ok": 0, "fail": 0}

    use_list = channels[: max_channels] if max_channels and max_channels > 0 else channels
    for idx, ch in enumerate(use_list, 1):
        cid = ch["id"]
        data, meta = fetch_program_list(
            base_url=base_url,
            channel_id=cid,
            riddle=riddle,
            time_ms=time_ms,
            extra_params=extra_params,
            ua=ua,
            timeout_s=timeout_s,
            opener=opener,
        )
        if isinstance(data, dict):
            epg_by_channel[cid] = data
            stats["ok"] += 1
        else:
            stats["fail"] += 1
            print(f"[WARN] channelId={cid} fetch_failed: {meta}", file=sys.stderr)

        if sleep_s and sleep_s > 0:
            time.sleep(float(sleep_s))

        if idx % 50 == 0:
            print(f"[INFO] progress {idx}/{len(use_list)} ok={stats['ok']} fail={stats['fail']}", file=sys.stderr)

    return epg_by_channel, stats


