#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络与网卡相关工具（net）

为什么要单独拆出来：
- `core.py` 只负责“频道抽取/生成 M3U”的业务逻辑
- 网络请求、绑定源 IP、从网卡取 IP 这类“运行环境相关”的内容，放在独立模块更清晰
"""

from __future__ import annotations

import http.client
import re
import subprocess
import urllib.request
from functools import partial
from typing import Optional


def is_url(s: str) -> bool:
    """
    作用：
    - 判断输入字符串是否为 `http://` URL。

    输入：
    - s: 任意字符串

    输出：
    - bool: 是 http URL 返回 True，否则 False
    """

    x = (s or "").strip().lower()
    return bool(x) and x.startswith("http://")


class _SourceAddrHTTPConnection(http.client.HTTPConnection):
    """
    作用：
    - 在建立 HTTP 连接前，把 socket 源地址 bind 到指定 source_ip。

    输入：
    - source_ip: 源 IP（为空表示不绑定）

    输出：
    - 无（副作用：connect() 时会影响连接使用的源地址）
    """

    def __init__(self, host: str, port: Optional[int] = None, *, source_ip: str = "", **kwargs):
        self._source_ip = (source_ip or "").strip()
        super().__init__(host, port=port, **kwargs)

    def connect(self) -> None:
        # http.client.HTTPConnection.connect() 会读取 self.source_address 并用于 socket.bind()
        if self._source_ip:
            self.source_address = (self._source_ip, 0)
        super().connect()


class _SourceAddrHTTPHandler(urllib.request.HTTPHandler):
    """
    作用：
    - 为 urllib 的 http:// 请求提供“绑定源 IP”的连接实现。

    输入：
    - source_ip: 源 IP（为空表示不绑定）

    输出：
    - 无（被 urllib 在打开 http URL 时调用）
    """

    def __init__(self, source_ip: str):
        super().__init__()
        self._source_ip = (source_ip or "").strip()

    def http_open(self, req: urllib.request.Request):
        conn_factory = partial(_SourceAddrHTTPConnection, source_ip=self._source_ip)
        return self.do_open(conn_factory, req)

def build_opener(source_ip: str) -> urllib.request.OpenerDirector:
    """
    作用：
    - 构建 urllib opener（可选绑定源 IP）。

    输入：
    - source_ip: 源 IP（为空表示不绑定）

    输出：
    - urllib.request.OpenerDirector: 用于 opener.open() 发起请求
    """

    if (source_ip or "").strip():
        return urllib.request.build_opener(_SourceAddrHTTPHandler(source_ip))
    return urllib.request.build_opener()


def get_ipv4_from_iface(iface: str) -> str:
    """
    作用：
    - 从指定网卡名获取 IPv4 地址（仅 Linux：依赖 `ip` 命令）。

    输入：
    - iface: 网卡名，例如 "eth1"

    输出：
    - str: 成功返回 IPv4（如 "10.170.162.12"），失败返回 ""
    """

    ifname = (iface or "").strip()
    if not ifname:
        return ""

    try:
        out = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "dev", ifname],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        m = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+)/\d+\b", out)
        if m:
            return m.group(1)
    except Exception:
        return ""

    return ""

