#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cron 模型
"""

from typing import Optional

from pydantic import BaseModel


class CronStatusResponse(BaseModel):
    """Cron 状态响应"""
    enabled: bool
    cron_expr: Optional[str] = None
    cron_cmd: Optional[str] = None
    next_run_info: Optional[str] = None


class CronSetupRequest(BaseModel):
    """Cron 设置请求"""
    mode: str  # "interval" | "cron"
    interval_hours: Optional[int] = None
    interval_minutes: Optional[int] = None
    cron_hour: Optional[str] = None
    cron_minute: Optional[str] = None
    source_iface: Optional[str] = None


class CronSetupResponse(BaseModel):
    """Cron 设置响应"""
    ok: bool
    message: str
    output: Optional[str] = None
    error: Optional[str] = None


class CronRemoveResponse(BaseModel):
    """Cron 移除响应"""
    ok: bool
    message: str
    output: Optional[str] = None
    error: Optional[str] = None

