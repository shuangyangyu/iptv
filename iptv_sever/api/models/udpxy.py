#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDPXY 模型
"""

from typing import Optional

from pydantic import BaseModel


class UdpxyStatusResponse(BaseModel):
    """UDPXY 状态响应"""
    running: bool
    pid: Optional[int] = None
    port: int
    bind_address: str
    source_iface: str
    max_connections: int
    connections: int = 0
    uptime: int = 0
    available: bool  # UDPXY 程序是否可用


class UdpxyStartResponse(BaseModel):
    """UDPXY 启动响应"""
    ok: bool
    message: str
    pid: Optional[int] = None
    error: Optional[str] = None


class UdpxyStopResponse(BaseModel):
    """UDPXY 停止响应"""
    ok: bool
    message: str
    error: Optional[str] = None


class UdpxyRestartResponse(BaseModel):
    """UDPXY 重启响应"""
    ok: bool
    message: str
    pid: Optional[int] = None


class UdpxyConfigResponse(BaseModel):
    """UDPXY 配置响应"""
    enabled: bool
    port: int
    bind_address: str
    source_iface: str
    max_connections: int
    log_file: Optional[str] = None
    pid_file: Optional[str] = None


class UdpxyConfigUpdateRequest(BaseModel):
    """UDPXY 配置更新请求"""
    enabled: Optional[bool] = None
    port: Optional[int] = None
    bind_address: Optional[str] = None
    source_iface: Optional[str] = None
    max_connections: Optional[int] = None
    log_file: Optional[str] = None
    pid_file: Optional[str] = None


class UdpxyConfigUpdateResponse(BaseModel):
    """UDPXY 配置更新响应"""
    ok: bool
    config: UdpxyConfigResponse
    message: Optional[str] = None

