#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置 API 路由
"""

from fastapi import APIRouter

from ..models.config import ConfigResponse, ConfigUpdateRequest, ConfigUpdateResponse
from ..services.state import get_config, update_config

router = APIRouter(prefix="/api/v1", tags=["配置管理"])


@router.get("/config", response_model=ConfigResponse)
async def api_get_config():
    """
    获取当前配置
    
    返回 IPTV Server 的所有配置项，包括 UDPXY 和回放配置
    """
    config = get_config()
    # 确保 udpxy 配置存在（如果不存在则使用默认值）
    if "udpxy" not in config or not config["udpxy"]:
        from ..utils.state import default_state
        default_config = default_state().get("config", {})
        config["udpxy"] = default_config.get("udpxy", {})
    # 确保 catchup 配置存在且包含必需字段（如果不存在或缺少字段则使用默认值）
    from ..utils.state import default_state
    default_config = default_state().get("config", {})
    default_catchup = default_config.get("catchup", {})
    
    if "catchup" not in config or not config["catchup"]:
        config["catchup"] = default_catchup.copy()
    else:
        # 确保必需字段存在
        catchup = config["catchup"]
        if not isinstance(catchup, dict):
            config["catchup"] = default_catchup.copy()
        elif "target_host" not in catchup or "target_port" not in catchup:
            # 合并默认值，确保必需字段存在
            config["catchup"] = {**default_catchup, **catchup}
    
    return config


@router.put("/config", response_model=ConfigUpdateResponse)
async def api_update_config(request: ConfigUpdateRequest):
    """
    更新配置
    
    只需传递需要更新的字段，未传递的配置项保持不变
    配置更新后会立即生效并持久化保存
    
    可以通过 udpxy 字段更新 UDPXY 配置，例如：
    {
        "udpxy": {
            "enabled": true,
            "port": 4022,
            "bind_address": "0.0.0.0",
            "source_iface": "eth1",
            "max_connections": 5
        }
    }
    
    可以通过 catchup 字段更新回放配置，例如：
    {
        "catchup": {
            "target_host": "10.255.129.26",
            "target_port": 6060,
            "virtual_domain": "hls.tvod_hls.zte.com"
        }
    }
    """
    updates = request.model_dump(exclude_unset=True)
    config = update_config(updates)
    # 确保 udpxy 配置存在
    if "udpxy" not in config or not config["udpxy"]:
        from ..utils.state import default_state
        default_config = default_state().get("config", {})
        config["udpxy"] = default_config.get("udpxy", {})
    # 确保 catchup 配置存在且包含必需字段
    from ..utils.state import default_state
    default_config = default_state().get("config", {})
    default_catchup = default_config.get("catchup", {})
    
    if "catchup" not in config or not config["catchup"]:
        config["catchup"] = default_catchup.copy()
    else:
        # 确保必需字段存在
        catchup = config["catchup"]
        if not isinstance(catchup, dict):
            config["catchup"] = default_catchup.copy()
        elif "target_host" not in catchup or "target_port" not in catchup:
            # 合并默认值，确保必需字段存在
            config["catchup"] = {**default_catchup, **catchup}
    
    return ConfigUpdateResponse(ok=True, config=ConfigResponse(**config))

