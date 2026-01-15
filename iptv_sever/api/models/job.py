#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务模型
"""

from typing import Optional

from pydantic import BaseModel

from .status import FileStatus, StatusResponse


class JobResponse(BaseModel):
    """任务执行响应"""
    ok: bool
    status: StatusResponse
    error: Optional[str] = None
    download_url: Optional[str] = None  # 生成文件的下载 URL（如果任务成功生成文件）

