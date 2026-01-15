#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志模型
"""

from typing import List

from pydantic import BaseModel


class LogEntry(BaseModel):
    """日志条目"""
    ts: int  # Unix 时间戳
    level: str  # "INFO" | "OK" | "WARN" | "ERROR"
    msg: str


class LogsResponse(BaseModel):
    """日志列表响应"""
    logs: List[LogEntry]


class ClearLogsResponse(BaseModel):
    """清空日志响应"""
    ok: bool

