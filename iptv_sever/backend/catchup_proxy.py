#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回看媒体反向代理辅助

直播：udpxy（组播 → HTTP）
回看：本模块把运营商 10.255 CDN 的 m3u8/.ts 改写成经本机代理，
      播放器只需访问局域网 IPTV Server，由服务器绑定 source_iface 去拉 IPTV 内网。
"""

from __future__ import annotations

import base64
import ipaddress
import re
import urllib.request
from typing import Callable, Optional, Tuple
from urllib.parse import urljoin, urlparse

from .net import _SourceAddrHTTPHandler, get_ipv4_from_iface

_URI_ATTR_RE = re.compile(r'URI="([^"]+)"', re.IGNORECASE)


def get_source_bind_ip(source_iface: str) -> str:
    return get_ipv4_from_iface((source_iface or "").strip())


def is_allowed_upstream_url(url: str) -> bool:
    """仅允许代理到运营商/内网，避免开放代理。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        host_l = host.lower()
        return host_l.endswith(".zte.com") or "tvod" in host_l or "epg" in host_l
    return bool(ip.is_private or ip in ipaddress.ip_network("100.64.0.0/10"))


def encode_upstream_token(url: str) -> str:
    raw = base64.urlsafe_b64encode((url or "").encode("utf-8")).decode("ascii")
    return raw.rstrip("=")


def decode_upstream_token(token: str) -> str:
    s = (token or "").strip()
    if not s:
        return ""
    try:
        pad = "=" * (-len(s) % 4)
        decoded = base64.urlsafe_b64decode(s + pad).decode("utf-8")
        if decoded.startswith("http://") or decoded.startswith("https://"):
            return decoded
    except Exception:
        pass
    from urllib.parse import unquote

    once = unquote(s)
    if once.startswith("http://") or once.startswith("https://"):
        return once
    return once


def build_media_proxy_url(proxy_base: str, upstream_url: str) -> str:
    base = (proxy_base or "").rstrip("/")
    return f"{base}?u={encode_upstream_token(upstream_url)}"


def rewrite_m3u8_to_proxy(
    content: bytes,
    *,
    playlist_url: str,
    proxy_base: str,
) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")

    out_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue

        if stripped.startswith("#"):
            def _repl(m: re.Match) -> str:
                raw = m.group(1)
                abs_url = urljoin(playlist_url, raw)
                if abs_url.startswith("http://") or abs_url.startswith("https://"):
                    return f'URI="{build_media_proxy_url(proxy_base, abs_url)}"'
                return m.group(0)

            out_lines.append(_URI_ATTR_RE.sub(_repl, line))
            continue

        abs_url = urljoin(playlist_url, stripped)
        if abs_url.startswith("http://") or abs_url.startswith("https://"):
            out_lines.append(build_media_proxy_url(proxy_base, abs_url))
        else:
            out_lines.append(line)

    return ("\r\n".join(out_lines) + "\r\n").encode("utf-8")


def looks_like_m3u8(content_type: str, content: bytes) -> bool:
    ct = (content_type or "").lower()
    if "mpegurl" in ct or "m3u8" in ct or ct.endswith("/m3u"):
        return True
    return content[:64].lstrip().lower().startswith(b"#extm3u")


def looks_like_ts(url: str, content_type: str) -> bool:
    path = (urlparse(url).path or "").lower()
    ct = (content_type or "").lower()
    return path.endswith(".ts") or "mp2t" in ct or "mpegts" in ct


def fetch_upstream(
    url: str,
    *,
    source_iface: str = "",
    user_agent: str = "Mozilla/5.0",
    timeout: float = 30,
    on_redirect: Optional[Callable[[str], None]] = None,
) -> Tuple[int, dict, bytes, str]:
    """绑定 source_iface 拉取上游。返回 (status, headers, body, final_url)。"""
    bind_ip = get_source_bind_ip(source_iface)

    class PreserveRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if on_redirect:
                on_redirect(newurl)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    handlers = [PreserveRedirect]
    if bind_ip:
        handlers.insert(0, _SourceAddrHTTPHandler(bind_ip))
    opener = urllib.request.build_opener(*handlers)

    req = urllib.request.Request(url)
    req.add_header("User-Agent", user_agent or "Mozilla/5.0")
    with opener.open(req, timeout=timeout) as resp:
        body = resp.read()
        headers = {k: v for k, v in resp.headers.items()}
        return int(resp.status), headers, body, (resp.geturl() or url)
