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
    
    import time
    
    if action == "start":
        result = start_udpxy()
        # 启动后等待一段时间，确保进程完全启动
        if result.get("ok"):
            time.sleep(0.8)  # 等待 0.8 秒让进程启动
    elif action == "stop":
        result = stop_udpxy()
    elif action == "restart":
        result = restart_udpxy()
        # 重启后等待一段时间
        if result.get("ok"):
            time.sleep(0.8)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    # 获取当前运行状态（启动/重启后需要等待后再检查）
    if action in ("start", "restart") and result.get("ok"):
        # 等待更长时间，然后重试检查状态
        max_retries = 8
        status = None
        for retry in range(max_retries):
            time.sleep(0.2)
            status = get_udpxy_status()
            if status.get("running"):
                break
        if status is None:
            status = get_udpxy_status()
    else:
        status = get_udpxy_status()
    
    # 如果启动成功但状态显示未运行，使用启动返回的 PID
    running = status.get("running", False)
    if action in ("start", "restart") and result.get("ok") and result.get("pid"):
        # 如果启动返回了 PID，即使状态检查暂时失败，也认为启动成功
        if not running:
            # 再次检查一次
            time.sleep(0.3)
            status = get_udpxy_status()
            running = status.get("running", False)
        # 如果启动返回了 PID，认为启动成功
        if result.get("pid") and not running:
            running = True  # 使用启动返回的 PID 作为成功标志
    
    return UdpxyActionResponse(
        ok=result.get("ok", False),
        message=result.get("message", ""),
        running=running,
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

