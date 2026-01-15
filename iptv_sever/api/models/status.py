#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
状态模型
"""

from typing import Optional

from pydantic import BaseModel

from .udpxy import UdpxyStatusResponse


class FileStatus(BaseModel):
    """文件状态"""
    exists: bool
    size: int
    mtime: int
    download_url: Optional[str] = None  # 文件下载 URL（如果文件存在）


class StatusResponse(BaseModel):
    """系统状态响应"""
    m3u: FileStatus
    epg: FileStatus
    last_job: Optional[str] = None  # "m3u" | "epg" | null
    last_job_rc: Optional[int] = None  # 0=成功，非0=失败，null=未执行
    last_job_at: Optional[int] = None  # Unix 时间戳
    udpxy: Optional[UdpxyStatusResponse] = None  # UDPXY 服务状态

