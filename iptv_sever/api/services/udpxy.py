#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDPXY 服务
"""

import logging
from typing import Any, Dict

from ..config import IPTV_SEVER_DIR
from ..utils.network import get_local_iface_ip
from ..utils.state import append_log, load_state, save_state

# 动态导入 backend 模块
import sys
from pathlib import Path

if IPTV_SEVER_DIR and str(IPTV_SEVER_DIR) not in sys.path:
    sys.path.insert(0, str(IPTV_SEVER_DIR))

from backend.udpxy_manager import UdpxyManager

logger = logging.getLogger(__name__)


def get_udpxy_base_url(cfg: Dict[str, Any]) -> str:
    """
    获取 UDPXY 基础 URL（从 local_iface 获取 IP，结合 UDPXY 配置的 port）
    
    Args:
        cfg: 配置字典，应包含 local_iface 字段
    
    Returns:
        UDPXY 基础 URL，例如 "http://192.168.1.250:4022"
    """
    # 获取 UDPXY 配置
    udpxy_config = get_udpxy_config()
    port = udpxy_config.get("port", 4022)
    
    # 从 local_iface 获取 IP
    ip = get_local_iface_ip(cfg)
    if ip:
        udpxy_base = f"http://{ip}:{port}"
        logger.info(f"从 local_iface 获取到 UDPXY 基础 URL: {udpxy_base} (port: {port})")
        return udpxy_base
    else:
        # 如果获取失败，使用默认值
        default_url = f"http://192.168.1.250:{port}"
        logger.warning(f"无法从 local_iface 获取 IP，使用默认 UDPXY 基础 URL: {default_url}")
        return default_url


def get_udpxy_config() -> Dict[str, Any]:
    """
    获取 UDPXY 配置
    
    从 state.json 的 config.udpxy 中读取，如果没有则使用默认值
    如果顶层 source_iface 存在，会同步到 udpxy 配置中
    """
    from ..utils.state import default_state
    
    state = load_state()
    cfg = state.get("config", {})
    default_cfg = default_state().get("config", {})
    
    # 从配置中读取 UDPXY 配置，如果没有则使用默认值
    udpxy_config = cfg.get("udpxy")
    
    # 如果 udpxy 配置不存在或者是 None，使用默认值
    if not udpxy_config or not isinstance(udpxy_config, dict):
        default_udpxy = default_cfg.get("udpxy", {})
        merged_config = default_udpxy.copy()
    else:
        # 合并默认值和保存的配置
        default_udpxy = default_cfg.get("udpxy", {})
        merged_config = default_udpxy.copy()
        # 使用保存的配置覆盖默认值
        for key, value in udpxy_config.items():
            if value is not None:
                merged_config[key] = value
    
    # 总是使用顶层的 source_iface（UDPXY 的 source_iface 应该与顶层配置同步）
    if "source_iface" in cfg and cfg["source_iface"]:
        merged_config["source_iface"] = cfg["source_iface"]
    
    # 确保所有必需字段都存在
    required_fields = {
        "enabled": True,
        "port": 4022,
        "bind_address": "0.0.0.0",
        "source_iface": "eth1",
        "max_connections": 5,
    }
    for key, default_value in required_fields.items():
        if key not in merged_config:
            merged_config[key] = default_value
    
    return merged_config


def save_udpxy_config(config: Dict[str, Any]) -> None:
    """
    保存 UDPXY 配置到 state.json
    """
    state = load_state()
    cfg = state.setdefault("config", {})
    cfg["udpxy"] = config
    save_state(state)


def get_udpxy_status() -> Dict[str, Any]:
    """
    获取 UDPXY 运行状态
    """
    config = get_udpxy_config()
    manager = UdpxyManager(config)
    return manager.get_status()


def start_udpxy() -> Dict[str, Any]:
    """
    启动 UDPXY 服务
    """
    config = get_udpxy_config()
    manager = UdpxyManager(config)
    
    available, msg = manager.check_available()
    
    if not available:
        result = {
            "ok": False,
            "error": msg,
            "message": msg,  # 添加 message 字段
        }
        return result
    
    success, message, pid = manager.start()
    
    if success:
        state = load_state()
        append_log(state, "INFO", f"UDPXY 启动成功 (PID: {pid})")
        save_state(state)
        result = {
            "ok": True,
            "message": message,
            "pid": pid,
        }
        return result
    else:
        state = load_state()
        append_log(state, "ERROR", f"UDPXY 启动失败: {message}")
        save_state(state)
        result = {
            "ok": False,
            "error": message,
            "message": message,  # 添加 message 字段
        }
        return result


def stop_udpxy() -> Dict[str, Any]:
    """
    停止 UDPXY 服务
    """
    config = get_udpxy_config()
    manager = UdpxyManager(config)
    
    success, message = manager.stop()
    
    if success:
        state = load_state()
        append_log(state, "INFO", "UDPXY 停止成功")
        save_state(state)
        result = {
            "ok": True,
            "message": message,
        }
        return result
    else:
        state = load_state()
        append_log(state, "WARN", f"UDPXY 停止: {message}")
        save_state(state)
        result = {
            "ok": False,
            "error": message,
            "message": message,  # 添加 message 字段
        }
        return result


def restart_udpxy() -> Dict[str, Any]:
    """
    重启 UDPXY 服务
    """
    # 先停止
    stop_result = stop_udpxy()
    
    # 再启动
    start_result = start_udpxy()
    
    if start_result.get("ok"):
        result = {
            "ok": True,
            "message": "UDPXY 重启成功",
            "pid": start_result.get("pid"),
        }
        return result
    else:
        result = {
            "ok": False,
            "error": start_result.get("error", "重启失败"),
            "message": start_result.get("error", "重启失败"),  # 添加 message 字段
        }
        return result


def update_udpxy_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新 UDPXY 配置
    """
    config = get_udpxy_config()
    
    # 允许更新的字段列表（白名单）
    allowed_keys = {
        "enabled",
        "port",
        "bind_address",
        "source_iface",
        "max_connections",
        "log_file",
        "pid_file",
    }
    
    # 更新配置（只更新允许的字段）
    for key, value in updates.items():
        if key in allowed_keys:
            config[key] = value
    
    # 保存配置
    save_udpxy_config(config)
    
    state = load_state()
    append_log(state, "INFO", "UDPXY 配置已更新")
    save_state(state)
    
    return {
        "ok": True,
        "config": config,
        "message": "配置已更新，需要重启 UDPXY 才能生效",
    }

