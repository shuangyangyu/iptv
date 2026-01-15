#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络接口 API 路由
"""

from typing import Optional

from fastapi import APIRouter

from ..models.network import (
    NetworkInterfaceDetailResponse,
    NetworkInterfacesDetailResponse,
    NetworkInterfacesResponse,
)
from ..services.network import (
    get_interfaces_detail_info,
    get_network_interfaces,
)

router = APIRouter(prefix="/api/v1", tags=["网络接口"])


@router.get("/interfaces", response_model=NetworkInterfacesResponse)
async def api_get_interfaces(physical: bool = False):
    """
    获取网络接口列表
    
    获取系统中所有网络接口的列表，支持过滤物理网卡。
    
    - **physical**: 如果为 True，仅返回通过 PIC 识别的真实物理网卡；否则返回所有网卡
    """
    return get_network_interfaces(physical_only=physical)


@router.get("/interfaces/{name}", response_model=NetworkInterfacesDetailResponse)
async def api_get_interface(name: str):
    """
    获取网络接口详细信息
    
    获取指定网络接口的详细信息，包括 IP、网关、MAC 地址、驱动、速度等。
    支持查询单个接口或使用特殊标识符。
    
    - **name**: 网卡名称或特殊标识符，可以是：
        - 接口名称（如 "ens192"）
        - "source_iface": 使用配置中的 source_iface
        - "local_iface": 使用配置中的 local_iface
        - 逗号分隔的多个接口名称（如 "ens160,ens192"）
        - "source_iface,local_iface": 同时使用配置中的 source_iface 和 local_iface
    """
    return get_interfaces_detail_info(interfaces=name)
