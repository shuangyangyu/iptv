#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络模型
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class NetworkResponse(BaseModel):
    """网络信息响应"""
    interface: str
    ip: Optional[str] = None
    gateway: Optional[str] = None


class NetworkInterface(BaseModel):
    """网络接口信息"""
    name: str
    status: Optional[str] = None  # "up" | "down" | "unknown"
    ip: Optional[str] = None
    has_ip: bool = False
    # 物理网卡特有字段（当 physical=True 时填充）
    pic_id: Optional[str] = None
    mac_address: Optional[str] = None
    type: Optional[str] = None  # "ethernet" | "wireless"
    driver: Optional[str] = None
    speed: Optional[str] = None
    duplex: Optional[str] = None


class NetworkInterfacesResponse(BaseModel):
    """网络接口列表响应"""
    interfaces: List[NetworkInterface]
    physical_only: bool = False  # 标识是否为仅物理网卡模式


class NetworkInterfaceDetailResponse(BaseModel):
    """网络接口详细信息响应"""
    name: str
    status: Optional[str] = None  # "up" | "down" | "unknown"
    ip: Optional[str] = None
    gateway: Optional[str] = None
    has_ip: bool = False
    mac_address: Optional[str] = None
    type: Optional[str] = None  # "ethernet" | "wireless"
    pic_id: Optional[str] = None
    driver: Optional[str] = None
    speed: Optional[str] = None
    duplex: Optional[str] = None


class NetworkInterfacesDetailResponse(BaseModel):
    """多个网络接口详细信息响应"""
    interfaces: List[NetworkInterfaceDetailResponse]


class CheckItem(BaseModel):
    """检测项"""
    category: str  # "network" | "udpxy" | "files" | "config" | "services"
    name: str  # 检测项名称
    status: str  # "ok" | "error" | "warn"
    message: str  # 检测结果消息
    details: Optional[Dict[str, Any]] = None  # 详细信息


class CheckCategory(BaseModel):
    """检测分类结果"""
    category: str
    ok: bool  # 该分类是否全部通过
    items: List[CheckItem]
    passed: int  # 通过项数
    failed: int  # 失败项数
    warnings: int  # 警告项数


class EnvironmentCheckResponse(BaseModel):
    """环境检测响应"""
    ok: bool  # 整体是否达标
    timestamp: int  # 检测时间戳
    summary: Dict[str, int]  # {"total": 15, "passed": 12, "failed": 2, "warnings": 1}
    categories: Dict[str, CheckCategory]  # 按分类组织的结果
    failed_items: List[CheckItem]  # 所有不合格项（方便快速查看）

