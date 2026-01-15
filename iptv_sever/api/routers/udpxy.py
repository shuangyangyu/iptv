#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDPXY 管理 API 路由
"""

from fastapi import APIRouter, HTTPException

from ..models.udpxy import (
    UdpxyConfigResponse,
    UdpxyConfigUpdateRequest,
    UdpxyConfigUpdateResponse,
    UdpxyStatusResponse,
)
from ..models.udpxy_action import UdpxyActionRequest, UdpxyActionResponse
from ..services.udpxy import (
    get_udpxy_config,
    get_udpxy_status,
    restart_udpxy,
    start_udpxy,
    stop_udpxy,
    update_udpxy_config,
)

router = APIRouter(prefix="/api/v1", tags=["UDPXY 管理"])


@router.get("/udpxy", response_model=UdpxyStatusResponse)
async def api_udpxy_status():
    """
    获取 UDPXY 运行状态
    
    检查 UDPXY 服务是否正在运行，返回进程信息和运行统计
    """
    return get_udpxy_status()


@router.post("/udpxy/actions", response_model=UdpxyActionResponse)
async def api_udpxy_action(request: UdpxyActionRequest):
    """
    执行 UDPXY 服务操作
    
    执行 UDPXY 服务的启动、停止或重启操作。
    
    - **action**: 要执行的操作
        - `start`: 启动 UDPXY 服务
        - `stop`: 停止 UDPXY 服务
        - `restart`: 重启 UDPXY 服务（先停止再启动）
    
    **请求示例**：
    ```json
    {
        "action": "start"
    }
    ```
    """
    action = request.action
    
    if action == "start":
        result = start_udpxy()
    elif action == "stop":
        result = stop_udpxy()
    elif action == "restart":
        result = restart_udpxy()
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    # 获取当前运行状态
    status = get_udpxy_status()
    
    return UdpxyActionResponse(
        ok=result.get("ok", False),
        message=result.get("message", ""),
        running=status.get("running", False),
        pid=result.get("pid") or status.get("pid"),
    )


@router.get("/udpxy/config", response_model=UdpxyConfigResponse)
async def api_udpxy_get_config():
    """
    获取 UDPXY 配置
    
    返回 UDPXY 的配置参数
    """
    config = get_udpxy_config()
    return config


@router.put("/udpxy/config", response_model=UdpxyConfigUpdateResponse)
async def api_udpxy_update_config(request: UdpxyConfigUpdateRequest):
    """
    更新 UDPXY 配置
    
    更新 UDPXY 配置参数，需要重启才能生效
    """
    updates = request.model_dump(exclude_unset=True)
    result = update_udpxy_config(updates)
    return result

