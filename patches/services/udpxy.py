#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""UDPXY 服务（配置来自 YAML）"""

import logging
import sys
from typing import Any, Dict

from ..config import IPTV_SEVER_DIR
from ..runtime_status import append_runtime_log
from ..utils.network import get_local_iface_ip

if IPTV_SEVER_DIR and str(IPTV_SEVER_DIR) not in sys.path:
    sys.path.insert(0, str(IPTV_SEVER_DIR))

from backend.udpxy_manager import UdpxyManager

logger = logging.getLogger(__name__)


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
    udpxy.setdefault("source_iface", "eth1")
    udpxy.setdefault("max_connections", 5)
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
