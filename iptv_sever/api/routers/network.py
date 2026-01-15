#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络 API 路由

注意：网络接口状态查询相关的 API 已移至 status.py
此文件保留用于未来可能的网络管理操作（如配置网络接口等）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["网络管理"])

# 网络接口状态查询 API 已移至 status.py
# 保留此文件用于未来可能的网络管理操作

