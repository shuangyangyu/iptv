#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
状态管理服务
"""

import logging
from pathlib import Path
from typing import Any, Dict

from ..config import OUT_DIR
from ..utils.network import get_local_iface_ip
from ..utils.state import load_state

logger = logging.getLogger(__name__)


def get_status() -> Dict[str, Any]:
    """
    获取系统状态：实时检查文件状态和 UDPXY 服务状态
    """
    state = load_state()
    cfg = state.get("config", {})
    st = state.get("status", {})
    
    # 获取 web_base_url（用于构建下载链接）
    web_base_url = get_server_base_url(cfg, port=8088)
    
    # 实时检查 M3U 文件状态
    m3u_path_str = cfg.get("output_m3u", "iptv.m3u")
    m3u_filename = Path(m3u_path_str).name
    m3u_path = OUT_DIR / m3u_filename
    if m3u_path.exists():
        st["m3u"] = {
            "exists": True,
            "size": m3u_path.stat().st_size,
            "mtime": int(m3u_path.stat().st_mtime),
            "download_url": f"{web_base_url}/out/{m3u_filename}",
        }
    else:
        st["m3u"] = {"exists": False, "size": 0, "mtime": 0, "download_url": None}
    
    # 实时检查 EPG 文件状态
    epg_path_str = cfg.get("epg_out", "epg.xml")
    epg_filename = Path(epg_path_str).name
    epg_path = OUT_DIR / epg_filename
    if epg_path.exists():
        st["epg"] = {
            "exists": True,
            "size": epg_path.stat().st_size,
            "mtime": int(epg_path.stat().st_mtime),
            "download_url": f"{web_base_url}/out/{epg_filename}",
        }
    else:
        st["epg"] = {"exists": False, "size": 0, "mtime": 0, "download_url": None}
    
    # 获取 UDPXY 服务状态
    try:
        from .udpxy import get_udpxy_status
        udpxy_status = get_udpxy_status()
        st["udpxy"] = udpxy_status
    except Exception as e:
        # 如果获取 UDPXY 状态失败，记录错误但不影响其他状态
        import logging
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
    
    return st


def get_server_base_url(cfg: Dict[str, Any], port: int = 8088) -> str:
    """
    获取服务器基础 URL（从 local_iface 获取 IP）
    
    Args:
        cfg: 配置字典，应包含 local_iface 字段
        port: 端口号，默认 8088
    
    Returns:
        服务器基础 URL，例如 "http://192.168.1.250:8088"
    """
    ip = get_local_iface_ip(cfg)
    if ip:
        base_url = f"http://{ip}:{port}"
        logger.info(f"从 local_iface 获取到服务器基础 URL: {base_url}")
        return base_url
    else:
        # 如果获取失败，使用默认值
        default_url = f"http://192.168.1.250:{port}"
        logger.warning(f"无法从 local_iface 获取 IP，使用默认值: {default_url}")
        return default_url


def get_config() -> Dict[str, Any]:
    """
    获取当前配置
    
    合并默认值，确保所有字段都有值而不是 None
    自动填充 udpxy_base 和 x_tvg_url（基于 local_iface）
    UDPXY 始终启用（use_udpxy 自动设置为 True）
    """
    from ..services.udpxy import get_udpxy_base_url
    from ..utils.state import default_state
    
    state = load_state()
    saved_config = state.get("config", {})
    default_config = default_state().get("config", {})
    
    # 合并默认值和保存的配置，保存的配置优先
    # 但是如果保存的配置中某个字段是 None，则使用默认值
    merged_config = default_config.copy()
    for key, value in saved_config.items():
        if value is not None:  # 只使用非 None 的值覆盖默认值
            # 如果是字典类型（如 udpxy、catchup），需要递归合并
            if isinstance(value, dict) and isinstance(merged_config.get(key), dict):
                merged_config[key] = {**merged_config[key], **value}
            else:
                merged_config[key] = value
    
    # 确保 catchup 配置存在且包含必需字段
    if "catchup" not in merged_config or not merged_config.get("catchup"):
        # 如果 catchup 不存在，使用默认值
        merged_config["catchup"] = default_config.get("catchup", {}).copy()
    else:
        # 确保必需字段存在
        catchup = merged_config["catchup"]
        if isinstance(catchup, dict):
            default_catchup = default_config.get("catchup", {})
            # 如果缺少必需字段，合并默认值
            if "target_host" not in catchup or "target_port" not in catchup:
                merged_config["catchup"] = {**default_catchup, **catchup}
    
    # UDPXY 始终启用（因为 UDPXY 是程序运行的前提）
    merged_config["use_udpxy"] = True
    
    # 自动填充 udpxy_base（从 local_iface 获取）
    # 始终自动填充，确保前端能正确显示 UDPXY 配置部分
    try:
        udpxy_base = get_udpxy_base_url(merged_config)
        if udpxy_base:
            merged_config["udpxy_base"] = udpxy_base
        elif not merged_config.get("udpxy_base"):
            # 如果自动获取失败且配置中没有值，使用默认值
            merged_config["udpxy_base"] = "http://192.168.1.250:4022"
    except Exception as e:
        logger.warning(f"自动填充 udpxy_base 失败: {e}")
        # 如果自动填充失败，确保至少有一个默认值
        if not merged_config.get("udpxy_base"):
            merged_config["udpxy_base"] = "http://192.168.1.250:4022"
    
    # x_tvg_url 是动态生成的，不应该在配置中保存或返回
    # 它会在 execute_job() 时自动从 local_iface 构建
    # 如果配置中有旧值，清除它，让系统自动生成
    if "x_tvg_url" in merged_config:
        merged_config["x_tvg_url"] = None
    
    return merged_config


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新配置
    
    Args:
        updates: 要更新的配置字段
    
    Returns:
        更新后的完整配置
    """
    from ..utils.state import append_log, load_state, save_state
    
    state = load_state()
    cfg = state.setdefault("config", {})
    
    # 允许更新的配置字段白名单
    allowed_keys = [
        "input_url", "source_iface", "local_iface", "output_m3u",
        "use_udpxy", "udpxy_base", "x_tvg_url", "timeout_s", "user_agent",
        "download_logos", "localize_logos", "logo_skip_existing", "logo_dir",
        "epg_out", "epg_base_url", "epg_riddle", "epg_time_ms",
        "epg_days_forward", "epg_days_back",
        "scheduler_mode", "scheduler_interval_hours", "scheduler_interval_minutes",
        "scheduler_cron_hour", "scheduler_cron_minute",
    ]
    
    for k in allowed_keys:
        if k in updates:
            cfg[k] = updates[k]
    
    # 处理 UDPXY 配置更新
    if "udpxy" in updates and isinstance(updates["udpxy"], dict):
        udpxy_updates = updates["udpxy"]
        udpxy_config = cfg.setdefault("udpxy", {})
        
        # UDPXY 配置允许的字段
        udpxy_allowed_keys = {
            "enabled",
            "port",
            "bind_address",
            "source_iface",
            "max_connections",
            "log_file",
            "pid_file",
        }
        
        # 更新 UDPXY 配置
        for key, value in udpxy_updates.items():
            if key in udpxy_allowed_keys and value is not None:
                udpxy_config[key] = value
        
        # 如果 source_iface 在顶层更新了，也同步更新到 udpxy
        if "source_iface" in updates and "source_iface" not in udpxy_updates:
            udpxy_config["source_iface"] = updates["source_iface"]
    
    # 处理回放配置更新
    if "catchup" in updates and isinstance(updates["catchup"], dict):
        catchup_updates = updates["catchup"]
        catchup_config = cfg.setdefault("catchup", {})
        
        # 回放配置允许的字段
        catchup_allowed_keys = {
            "target_host",
            "target_port",
            "virtual_domain",
        }
        
        # 更新回放配置
        for key, value in catchup_updates.items():
            if key in catchup_allowed_keys and value is not None:
                catchup_config[key] = value
    
    append_log(state, "INFO", "已保存配置")
    save_state(state)
    
    # 返回完整配置（合并默认值）
    return get_config()

