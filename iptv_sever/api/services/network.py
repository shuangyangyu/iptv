#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络服务
"""

from pathlib import Path
from typing import Any, Dict, Optional

from ..config import IPTV_SEVER_DIR
from ..utils.network import (
    get_all_interfaces,
    get_interface_detail,
    get_physical_interfaces,
)


def get_interfaces_detail_info(interfaces: Optional[str] = None) -> Dict[str, Any]:
    """
    获取多个网络接口的详细信息
    
    Args:
        interfaces: 网卡名称，可以是：
            - 逗号分隔的多个接口名称（如 "ens160,ens192"）
            - 单个接口名称（如 "ens192"）
            - "source_iface": 使用配置中的 source_iface
            - "local_iface": 使用配置中的 local_iface
            - "source_iface,local_iface": 同时使用配置中的 source_iface 和 local_iface
            - None: 默认同时返回 source_iface 和 local_iface 的信息
    
    Returns:
        包含接口列表的字典
    """
    from .state import get_config
    
    # 使用 get_config() 而不是 load_state()，确保获取合并后的配置（包含默认值）
    cfg = get_config()
    
    # 确定要查询的接口名称列表
    iface_names = []
    
    if interfaces is None:
        # 默认同时返回 source_iface 和 local_iface
        source_iface = cfg.get("source_iface")
        local_iface = cfg.get("local_iface")
        
        # 确保 source_iface 和 local_iface 是有效的字符串（非空）
        if source_iface and isinstance(source_iface, str) and source_iface.strip():
            iface_names.append(source_iface.strip())
        if local_iface and isinstance(local_iface, str) and local_iface.strip():
            local_iface = local_iface.strip()
            if local_iface not in iface_names:
                iface_names.append(local_iface)
        
        # 如果都没有配置，使用默认值
        if not iface_names:
            iface_names = ["eth1"]
    else:
        # 解析接口名称（支持逗号分隔）
        interface_list = [i.strip() for i in interfaces.split(",") if i.strip()]
        
        for iface in interface_list:
            if iface == "source_iface":
                source_iface = cfg.get("source_iface")
                if source_iface and isinstance(source_iface, str) and source_iface.strip():
                    iface_names.append(source_iface.strip())
            elif iface == "local_iface":
                local_iface = cfg.get("local_iface")
                if local_iface and isinstance(local_iface, str) and local_iface.strip():
                    iface_names.append(local_iface.strip())
            else:
                # 直接使用传入的接口名称
                if iface:
                    iface_names.append(iface)
    
    # 去重
    iface_names = list(dict.fromkeys(iface_names))  # 保持顺序的去重
    
    # 获取所有接口的详细信息
    interfaces_detail = []
    for iface_name in iface_names:
        try:
            detail = get_interface_detail(iface_name)
            interfaces_detail.append(detail)
        except Exception as e:
            # 如果某个接口获取失败，记录错误但继续处理其他接口
            import logging
            logging.warning(f"获取接口 {iface_name} 的详细信息失败: {e}")
            # 返回一个包含错误信息的接口详情
            interfaces_detail.append({
                "name": iface_name,
                "status": "unknown",
                "ip": None,
                "gateway": None,
                "has_ip": False,
                "mac_address": None,
                "type": None,
                "pic_id": None,
                "driver": None,
                "speed": None,
                "duplex": None,
            })
    
    return {
        "interfaces": interfaces_detail,
    }


def get_network_interfaces(physical_only: bool = False) -> Dict[str, Any]:
    """
    获取网络接口列表
    
    Args:
        physical_only: 如果为 True，仅返回物理网卡；否则返回所有网卡
    
    Returns:
        包含接口列表的字典
    """
    if physical_only:
        interfaces = get_physical_interfaces()
    else:
        interfaces = get_all_interfaces()
    
    return {
        "interfaces": interfaces,
        "physical_only": physical_only,
    }

