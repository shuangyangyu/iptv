#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""网络环境自检：双网卡 / IPTV 网关 / DNS / 频道源 / udpxy / 回看入口。"""

from __future__ import annotations

import ipaddress
import logging
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from iptv_sever.backend.net import build_opener, get_ipv4_from_iface

logger = logging.getLogger(__name__)

# 上次检测结果（供 MQTT / HTTP 读取）
_last_diag: Dict[str, Any] = {}


def get_last_diag() -> Dict[str, Any]:
    return dict(_last_diag) if _last_diag else {}


def _check(
    name: str,
    ok: bool,
    detail: str = "",
    *,
    critical: bool = True,
) -> Dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "critical": bool(critical),
        "detail": detail or "",
    }


def _iface_state(iface: str) -> Tuple[bool, str, str]:
    """返回 (up, ipv4, detail)。"""
    ifname = (iface or "").strip()
    if not ifname:
        return False, "", "网卡名为空"
    try:
        link = subprocess.check_output(
            ["ip", "-o", "link", "show", "dev", ifname],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        )
    except Exception as e:
        return False, "", f"无法读取网卡: {e}"
    up = " state UP " in f" {link} " or ",UP," in link or "UP," in link.split(":")[-1]
    ip = get_ipv4_from_iface(ifname)
    if not up:
        return False, ip, "链路未 UP"
    if not ip:
        return False, "", "无 IPv4（DHCP/地址异常）"
    return True, ip, ip


def _ping(host: str, *, iface: str = "", src_ip: str = "", timeout_s: float = 2.0) -> Tuple[bool, str]:
    host = (host or "").strip()
    if not host:
        return False, "目标为空"

    # 优先系统 ping（宿主机有；精简容器可能没有）
    for ping_bin in ("ping", "/usr/bin/ping", "/bin/ping"):
        cmd = [ping_bin, "-c", "1", "-W", str(max(1, int(timeout_s)))]
        if iface:
            cmd.extend(["-I", iface])
        cmd.append(host)
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s + 2,
            )
            if r.returncode == 0:
                return True, "reachable"
            # 二进制存在但不通
            if r.returncode is not None and "No such file" not in (r.stderr or ""):
                return False, (r.stderr or r.stdout or "ping failed").strip()[:120]
        except FileNotFoundError:
            continue
        except Exception as e:
            if "No such file" in str(e):
                continue
            return False, str(e)

    # 无 ping：UDP 探测触发 ARP，再读邻居表
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(max(0.5, timeout_s))
        if src_ip:
            try:
                s.bind((src_ip, 0))
            except OSError:
                pass
        try:
            s.sendto(b"iptv-diag", (host, 33434))
            try:
                s.recvfrom(64)
            except socket.timeout:
                pass
        finally:
            s.close()
        out = subprocess.check_output(
            ["ip", "neigh", "show", host],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
        if not out:
            return False, "no ARP neighbor"
        low = out.lower()
        if "failed" in low:
            return False, out[:120]
        if any(x in low for x in ("reachable", "stale", "delay", "probe", "permanent")):
            return True, out[:120]
        if "lladdr" in low:
            return True, out[:120]
        return False, out[:120]
    except Exception as e:
        return False, str(e)[:120]


def _resolve(host: str, timeout_s: float = 3.0) -> Tuple[bool, str]:
    host = (host or "").strip()
    if not host:
        return False, "空主机名"
    try:
        socket.setdefaulttimeout(timeout_s)
        infos = socket.getaddrinfo(host, None, socket.AF_INET)
        ips = sorted({i[4][0] for i in infos})
        if not ips:
            return False, "无 A 记录"
        return True, ",".join(ips[:4])
    except Exception as e:
        return False, str(e)
    finally:
        socket.setdefaulttimeout(None)


def _http_get(
    url: str,
    *,
    bind_ip: str = "",
    timeout_s: float = 8.0,
    method: str = "GET",
) -> Tuple[bool, str]:
    url = (url or "").strip()
    if not url.startswith("http://"):
        return False, "仅支持 http://"
    try:
        opener = build_opener(bind_ip)
        req = urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": "iptv-diag/1.0"},
        )
        with opener.open(req, timeout=timeout_s) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            data = resp.read(256)
            return 200 <= int(code) < 400, f"HTTP {code} bytes={len(data)}"
    except urllib.error.HTTPError as e:
        # 部分 EPG POST 可能 405/400，但能连上算半通；这里 GET 频道列表应 200
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:160]


def _tcp_connect(host: str, port: int, *, timeout_s: float = 3.0) -> Tuple[bool, str]:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return True, f"{host}:{port} open"
    except Exception as e:
        return False, str(e)[:120]


def _looks_like_home_lan(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        # 曾出现的错误 DHCP：192.168.110.0/24
        return addr in ipaddress.ip_network("192.168.110.0/24")
    except Exception:
        return False


def _looks_like_iptv(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr in ipaddress.ip_network("10.170.0.0/16")
    except Exception:
        return False


def run_network_diag(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    执行一轮网络自检。

    返回:
      {
        ok: bool,           # 所有 critical 检查通过
        at: epoch,
        summary: str,
        checks: [...]
      }
    """
    global _last_diag
    from .state import get_config

    cfg = dict(cfg or get_config())
    checks: List[Dict[str, Any]] = []

    local_iface = str(cfg.get("local_iface") or "ens160")
    source_iface = str(cfg.get("source_iface") or "ens192")
    iptv_gw = str(cfg.get("iptv_gateway") or "10.170.160.1")
    input_url = str(cfg.get("input_url") or "")
    epg_base = str(cfg.get("epg_base_url") or "")
    catchup = cfg.get("catchup") or {}
    catchup_host = str(catchup.get("target_host") or "")
    catchup_port = int(catchup.get("target_port") or 6060)

    # 1) LAN 网卡
    ok, ip, detail = _iface_state(local_iface)
    checks.append(_check(f"local_iface:{local_iface}", ok, detail))

    # 2) IPTV 网卡
    ok, sip, detail = _iface_state(source_iface)
    checks.append(_check(f"source_iface:{source_iface}", ok, detail))

    # 3) IPTV 地址是否像上游（非家里 VLAN110 DHCP）
    if sip:
        if _looks_like_home_lan(sip):
            checks.append(
                _check(
                    "source_ip_range",
                    False,
                    f"{sip} 像家里 VLAN110 DHCP，不是 IPTV 上游",
                )
            )
        elif _looks_like_iptv(sip):
            checks.append(_check("source_ip_range", True, f"{sip} 在 10.170.0.0/16"))
        else:
            checks.append(
                _check(
                    "source_ip_range",
                    True,
                    f"{sip}（非 10.170，请确认是否为当前运营商网段）",
                    critical=False,
                )
            )
    else:
        checks.append(_check("source_ip_range", False, "无源网卡 IP"))

    # 4) IPTV 网关
    ok, detail = _ping(iptv_gw, iface=source_iface if sip else "", src_ip=sip)
    checks.append(_check(f"iptv_gateway:{iptv_gw}", ok, detail))

    # 5) DNS yepg
    host = urlparse(input_url).hostname or "yepg.99tv.com.cn"
    ok, detail = _resolve(host)
    checks.append(_check(f"dns:{host}", ok, detail))

    # 6) 频道列表（绑 IPTV 口）
    if input_url:
        ok, detail = _http_get(input_url, bind_ip=sip, timeout_s=10.0)
        checks.append(_check("http_channels", ok, detail))
    else:
        checks.append(_check("http_channels", False, "未配置 input_url"))

    # 7) EPG 主机 DNS（可选连通）
    epg_host = urlparse(epg_base).hostname or ""
    if epg_host:
        ok, detail = _resolve(epg_host)
        checks.append(_check(f"dns:{epg_host}", ok, detail, critical=False))

    # 8) 回看入口 TCP
    if catchup_host:
        ok, detail = _tcp_connect(catchup_host, catchup_port)
        checks.append(_check(f"catchup:{catchup_host}:{catchup_port}", ok, detail))
    else:
        checks.append(_check("catchup", False, "未配置 catchup.target_host"))

    # 9) udpxy 进程
    bound = ""
    try:
        from .udpxy import get_udpxy_status

        st = get_udpxy_status()
        running = bool(st.get("running"))
        bound = str(st.get("multicast_bind_ip") or "").strip()
        checks.append(
            _check(
                "udpxy",
                running,
                f"running={running} pid={st.get('pid')} iface={st.get('source_iface')}",
            )
        )
    except Exception as e:
        running = False
        checks.append(_check("udpxy", False, str(e)))

    # 10) udpxy 组播绑定 IP 必须等于源网卡当前地址（DHCP 续租会变）
    if running and sip:
        if bound:
            checks.append(
                _check(
                    "udpxy_bind_ip",
                    bound == sip,
                    f"udpxy={bound} iface={sip}",
                )
            )
        else:
            checks.append(
                _check(
                    "udpxy_bind_ip",
                    False,
                    "无法解析 udpxy 组播绑定地址",
                    critical=False,
                )
            )

    critical_fail = [c for c in checks if c["critical"] and not c["ok"]]
    warn_fail = [c for c in checks if (not c["critical"]) and not c["ok"]]
    ok_all = len(critical_fail) == 0
    fail_names = ", ".join(c["name"] for c in critical_fail) or "none"
    summary = "OK" if ok_all else f"FAIL: {fail_names}"

    # 给人看的明细（HA 传感器属性 / 卡片展示）
    lines = []
    for c in checks:
        mark = "✓" if c["ok"] else "✗"
        lines.append(f"{mark} {c['name']}: {c.get('detail') or ''}".strip())
    detail_text = "\n".join(lines)

    result = {
        "ok": ok_all,
        "at": int(time.time()),
        "summary": summary,
        "detail": detail_text,
        "fail": [c["name"] for c in critical_fail],
        "warn": [c["name"] for c in warn_fail],
        "local_iface": local_iface,
        "source_iface": source_iface,
        "source_ip": sip,
        "checks": checks,
    }
    _last_diag = result
    logger.info(f"网络自检完成: {summary}")
    return result
