#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cron API 路由
"""

from fastapi import APIRouter

from ..models.cron import CronRemoveResponse, CronSetupRequest, CronSetupResponse, CronStatusResponse
from ..services.cron import get_cron_status, remove_cron, setup_cron

router = APIRouter(prefix="/api/v1", tags=["定时任务"])


@router.get("/cron", response_model=CronStatusResponse)
async def api_cron_status():
    """
    获取 Cron 任务状态
    
    检查当前系统是否已设置 Cron 任务
    """
    return get_cron_status()


@router.post("/cron", response_model=CronSetupResponse)
async def api_cron_setup(request: CronSetupRequest):
    """
    设置 Cron 任务
    
    支持间隔模式（interval）和 Cron 模式（cron）
    """
    return setup_cron(
        mode=request.mode,
        interval_hours=request.interval_hours,
        interval_minutes=request.interval_minutes,
        cron_hour=request.cron_hour,
        cron_minute=request.cron_minute,
        source_iface=request.source_iface,
    )


@router.delete("/cron", response_model=CronRemoveResponse)
async def api_cron_remove():
    """
    移除 Cron 任务
    
    移除已设置的 Cron 任务
    """
    return remove_cron()

