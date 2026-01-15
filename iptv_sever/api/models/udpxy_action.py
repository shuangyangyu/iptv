#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDPXY 操作请求和响应模型
"""

from typing import Literal

from pydantic import BaseModel, Field


class UdpxyActionRequest(BaseModel):
    """UDPXY 操作请求"""
    action: Literal["start", "stop", "restart"] = Field(
        ...,
        description="要执行的操作：start（启动）、stop（停止）、restart（重启）"
    )


class UdpxyActionResponse(BaseModel):
    """UDPXY 操作响应"""
    ok: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    running: bool = Field(..., description="服务当前运行状态")
    pid: int | None = Field(None, description="进程 ID（如果服务运行中）")
