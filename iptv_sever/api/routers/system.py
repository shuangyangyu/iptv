#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统管理 API 路由
"""

from fastapi import APIRouter

from ..models.network import EnvironmentCheckResponse
from ..services.environment_check import check_environment

router = APIRouter(prefix="/api/v1", tags=["系统管理"])


@router.post("/system/health-check", response_model=EnvironmentCheckResponse)
async def api_health_check():
    """
    系统健康检查
    
    执行全面的系统环境检测，包括网络、UDPXY、文件系统、配置和服务等各个方面。
    检测结果会记录到日志系统中。
    
    **检测项目**：
    - **网络配置检测**：源网络接口、本地网络接口、M3U/EPG 源地址连通性
    - **UDPXY 服务检测**：程序安装、服务运行状态、端口监听、状态接口可访问性
    - **文件系统检测**：输出目录可写性、M3U/EPG 文件存在性和时效性、日志文件可写性
    - **配置完整性检测**：必要配置项、配置一致性
    - **系统服务检测**：API 服务运行状态、定时任务配置状态
    
    **返回结果**：
    - `ok`: 整体是否达标（只要有 error 项就不达标）
    - `timestamp`: 检测时间戳
    - `summary`: 统计信息（总项数、通过数、失败数、警告数）
    - `categories`: 按分类组织的结果
    - `failed_items`: 所有不合格项（error 和 warn）的列表
    """
    return check_environment()
