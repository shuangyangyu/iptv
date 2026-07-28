#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
状态 / 配置服务（配置来自 YAML，状态来自内存 + 磁盘文件探测）
"""

import logging
from pathlib import Path
from typing import Any, Dict

from ..config import OUT_DIR
from ..utils.network import get_local_iface_ip

logger = logging.getLogger(__name__)

# m3u 任务检测到的 catchup 可写回内存覆盖（不改 YAML）
_catchup_override: Dict[str, Any] = {}


def set_catchup_override(
    target_host: str = None,
    target_port: int = None,
    virtual_domain: str = None,
) -> None:
    global _catchup_override
    cur = dict(_catchup_override)
    if target_host:
        cur["target_host"] = target_host
    if target_port:
        cur["target_port"] = int(target_port)
    if virtual_domain:
        cur["virtual_domain"] = virtual_domain
    _catchup_override = cur


def get_status() -> Dict[str, Any]:
    """实时检查文件状态和 UDPXY 服务状态。"""
    from ..runtime_status import get_runtime_status

    cfg = get_config()
    st = get_runtime_status()
    web_base_url = get_server_base_url(cfg, port=int(cfg.get("http_port") or 8088))

    out_dir_abs = OUT_DIR if OUT_DIR.is_absolute() else OUT_DIR.resolve()
    m3u_filename = Path(cfg.get("output_m3u", "iptv.m3u")).name
    m3u_path = out_dir_abs / m3u_filename
    if m3u_path.exists():
        st["m3u"] = {
            "exists": True,
            "size": m3u_path.stat().st_size,
            "mtime": int(m3u_path.stat().st_mtime),
            "download_url": f"{web_base_url}/out/{m3u_filename}",
        }
    else:
        st["m3u"] = {
            "exists": False,
            "size": 0,
            "mtime": 0,
            "download_url": None,
        }

    aptv_filename = Path(cfg.get("output_m3u_aptv") or "iptv-aptv.m3u").name
    aptv_path = out_dir_abs / aptv_filename
    if aptv_path.exists():
        st["m3u_aptv"] = {
            "exists": True,
            "size": aptv_path.stat().st_size,
            "mtime": int(aptv_path.stat().st_mtime),
            "download_url": f"{web_base_url}/out/{aptv_filename}",
        }
    else:
        st["m3u_aptv"] = {
            "exists": False,
            "size": 0,
            "mtime": 0,
            "download_url": None,
        }

    epg_filename = Path(cfg.get("epg_out", "epg.xml")).name
    epg_path = out_dir_abs / epg_filename
    if epg_path.exists():
        st["epg"] = {
            "exists": True,
            "size": epg_path.stat().st_size,
            "mtime": int(epg_path.stat().st_mtime),
            "download_url": f"{web_base_url}/out/{epg_filename}",
        }
    else:
        st["epg"] = {
            "exists": False,
            "size": 0,
            "mtime": 0,
            "download_url": None,
        }

    try:
        from .udpxy import get_udpxy_status

        st["udpxy"] = get_udpxy_status()
    except Exception as e:
        logging.warning(f"获取 UDPXY 状态失败: {e}")
        st["udpxy"] = {
            "running": False,
            "pid": None,
            "port": 4022,
            "bind_address": "0.0.0.0",
            "source_iface": cfg.get("source_iface", "eth1"),
            "max_connections": 5,
            "connections": 0,
            "uptime": 0,
            "available": False,
        }

    st["health"] = "online"
    return st


def get_server_base_url(cfg: Dict[str, Any], port: int = 8088) -> str:
    ip = get_local_iface_ip(cfg)
    if ip:
        return f"http://{ip}:{port}"
    default_url = f"http://192.168.1.250:{port}"
    logger.warning(f"无法从 local_iface 获取 IP，使用默认值: {default_url}")
    return default_url


def get_config() -> Dict[str, Any]:
    """从 YAML 加载并展平；自动填充 udpxy_base。"""
    from ..settings import get_runtime_config
    from .udpxy import get_udpxy_base_url

    merged = get_runtime_config()
    merged["use_udpxy"] = True

    if _catchup_override:
        catchup = dict(merged.get("catchup") or {})
        catchup.update(_catchup_override)
        merged["catchup"] = catchup

    try:
        udpxy_base = get_udpxy_base_url(merged)
        if udpxy_base:
            merged["udpxy_base"] = udpxy_base
        elif not merged.get("udpxy_base"):
            merged["udpxy_base"] = "http://192.168.1.250:4022"
    except Exception as e:
        logger.warning(f"自动填充 udpxy_base 失败: {e}")
        if not merged.get("udpxy_base"):
            merged["udpxy_base"] = "http://192.168.1.250:4022"

    merged["x_tvg_url"] = None
    return merged


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """配置已改为 YAML，禁止运行时写入。"""
    raise RuntimeError("配置请修改 config.yaml 后重启（或 SIGHUP），不再支持 HTTP/API 写配置")


def publish_status_mqtt() -> None:
    try:
        from iptv_sever.mqtt import publish_all_status

        publish_all_status(get_status())
    except Exception as e:
        logger.debug(f"MQTT 状态发布跳过: {e}")
