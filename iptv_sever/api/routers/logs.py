#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志 API 路由
"""

from fastapi import APIRouter, Query

from ..models.log import ClearLogsResponse, LogsResponse
from ..services.log import clear_logs, get_logs

router = APIRouter(prefix="/api/v1", tags=["日志管理"])


@router.get("/logs", response_model=LogsResponse)
async def api_logs(limit: int = Query(200, ge=1, le=400)):
    """
    获取日志列表
    
    支持 limit 参数限制返回的日志条数
    """
    logs = get_logs(limit)
    return LogsResponse(logs=logs)


@router.post("/logs/clear", response_model=ClearLogsResponse)
async def api_clear_logs():
    """
    清空日志
    
    清空所有日志记录
    """
    clear_logs()
    return ClearLogsResponse(ok=True)

