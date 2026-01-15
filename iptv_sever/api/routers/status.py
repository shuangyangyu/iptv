#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
状态 API 路由
"""

from fastapi import APIRouter

from ..models.status import StatusResponse
from ..services.state import get_status

router = APIRouter(prefix="/api/v1", tags=["系统状态"])


@router.get("/status", response_model=StatusResponse)
async def api_status():
    """
    获取系统状态
    
    实时检查 M3U 和 EPG 文件状态（存在性、大小、修改时间）
    返回最后执行的任务信息
    """
    status = get_status()
    return status

