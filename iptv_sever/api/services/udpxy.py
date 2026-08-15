#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UDPXY 服务（配置来自 YAML）"""

import logging
import sys
import threading
import time
from typing import Any, Dict

from ..config import IPTV_SEVER_DIR
from ..runtime_status import append_runtime_log
from ..utils.network import get_local_iface_ip

if IPTV_SEVER_DIR and str(IPTV_SEVER_DIR) not in sys.path:
    sys.path.insert(0, str(IPTV_SEVER_DIR))

from backend.udpxy_manager import UdpxyManager

logger = logging.getLogger(__name__)

_ensure_lock = threading.Lock()
_last_rebind_at = 0.0
_REBIND_COOLDOWN_S = 60.0


def get_udpxy_base_url(cfg: Dict[str, Any]) -> str:
    udpxy_config = cfg.get("udpxy") if isinstance(cfg.get("udpxy"), dict) else None
    if not udpxy_config:
        udpxy_config = get_udpxy_config()
    port = udpxy_config.get("port", 4022)
    ip = get_local_iface_ip(cfg)
    if ip:
        return f"http://{ip}:{port}"
    return f"http://192.168.1.250:{port}"


def get_udpxy_config() -> Dict[str, Any]:
    from .state import get_config

    cfg = get_config()
    udpxy = dict(cfg.get("udpxy") or {})
    if cfg.get("source_iface"):
        udpxy["source_iface"] = cfg["source_iface"]
    udpxy.setdefault("enabled", True)
    udpxy.setdefault("port", 4022)
    udpxy.setdefault("bind_address", "0.0.0.0")
    udpxy.setdefault("backend_port", 14022)
    udpxy.setdefault("backend_bind", "127.0.0.1")
    udpxy.setdefault("source_iface", "eth1")
    udpxy.setdefault("max_connections", 5)
    udpxy.setdefault("buffer_size", "2Mb")
    udpxy.setdefault("log_file", "/var/log/udpxy.log")
    udpxy.setdefault("pid_file", "/tmp/udpxy.pid")
    return udpxy


def save_udpxy_config(config: Dict[str, Any]) -> None:
    raise RuntimeError("UDPXY 配置请修改 config.yaml 后重启")


def get_udpxy_status() -> Dict[str, Any]:
    return UdpxyManager(get_udpxy_config()).get_status()


def start_udpxy() -> Dict[str, Any]:
    manager = UdpxyManager(get_udpxy_config())
    available, msg = manager.check_available()
    if not available:
        return {"ok": False, "error": msg, "message": msg}
    success, message, pid = manager.start()
    if success:
        append_runtime_log("INFO", f"UDPXY 启动成功 (PID: {pid})")
        return {"ok": True, "message": message, "pid": pid}
    append_runtime_log("ERROR", f"UDPXY 启动失败: {message}")
    return {"ok": False, "error": message, "message": message}


def stop_udpxy() -> Dict[str, Any]:
    success, message = UdpxyManager(get_udpxy_config()).stop()
    if success:
        append_runtime_log("INFO", "UDPXY 停止成功")
        return {"ok": True, "message": message}
    append_runtime_log("WARN", f"UDPXY 停止: {message}")
    return {"ok": False, "error": message, "message": message}


def restart_udpxy() -> Dict[str, Any]:
    stop_udpxy()
    start_result = start_udpxy()
    if start_result.get("ok"):
        return {
            "ok": True,
            "message": "UDPXY 重启成功",
            "pid": start_result.get("pid"),
        }
    return {
        "ok": False,
        "error": start_result.get("error", "重启失败"),
        "message": start_result.get("error", "重启失败"),
    }


def update_udpxy_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("UDPXY 配置请修改 config.yaml 后重启")


def ensure_udpxy_bound_to_source_ip() -> Dict[str, Any]:
    """
    专网 DHCP 换地址后，udpxy 仍用启动时的组播绑定 IP，拉流会 500。
    发现 source_iface 当前 IP 与 /status 的 Multicast address 不一致时重启。
    """
    global _last_rebind_at

    cfg = get_udpxy_config()
    if not cfg.get("enabled", True):
        return {"ok": True, "action": "skip", "reason": "udpxy disabled"}

    from iptv_sever.backend.net import get_ipv4_from_iface

    source_iface = str(cfg.get("source_iface") or "ens192")
    iface_ip = (get_ipv4_from_iface(source_iface) or "").strip()
    if not iface_ip:
        return {"ok": True, "action": "skip", "reason": f"{source_iface} 无 IPv4"}

    if not _ensure_lock.acquire(blocking=False):
        return {"ok": True, "action": "skip", "reason": "rebind in progress"}
    try:
        st = get_udpxy_status()
        if not st.get("running"):
            result = start_udpxy()
            result["action"] = "start"
            result["iface_ip"] = iface_ip
            return result

        bound = (st.get("multicast_bind_ip") or "").strip()
        if not bound:
            return {
                "ok": True,
                "action": "skip",
                "reason": "无法解析 udpxy 组播绑定地址",
                "iface_ip": iface_ip,
            }
        if bound == iface_ip:
            return {
                "ok": True,
                "action": "none",
                "iface_ip": iface_ip,
                "bound_ip": bound,
            }

        now = time.monotonic()
        if now - _last_rebind_at < _REBIND_COOLDOWN_S:
            return {
                "ok": True,
                "action": "cooldown",
                "bound_ip": bound,
                "iface_ip": iface_ip,
            }

        logger.warning(
            "udpxy 组播绑定 %s 与 %s 当前地址 %s 不一致，重启 udpxy",
            bound,
            source_iface,
            iface_ip,
        )
        append_runtime_log(
            "WARN",
            f"UDPXY 重绑: {bound} → {iface_ip} ({source_iface})",
        )
        _last_rebind_at = now
        result = restart_udpxy()
        result["action"] = "restart"
        result["bound_ip"] = bound
        result["iface_ip"] = iface_ip
        if result.get("ok"):
            logger.info("UDPXY 已按新地址 %s 重绑", iface_ip)
        else:
            logger.error("UDPXY 重绑失败: %s", result.get("message"))
        return result
    finally:
        _ensure_lock.release()
