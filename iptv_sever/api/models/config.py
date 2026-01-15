#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置模型
"""

from typing import Dict, Optional

from pydantic import BaseModel

from .udpxy import UdpxyConfigResponse, UdpxyConfigUpdateRequest


class CatchupConfigResponse(BaseModel):
    """回放配置响应"""
    target_host: str
    target_port: int
    virtual_domain: Optional[str] = None


class ConfigResponse(BaseModel):
    """配置响应"""
    input_url: str
    source_iface: str
    local_iface: Optional[str] = None
    output_m3u: str
    use_udpxy: Optional[bool] = None
    udpxy_base: Optional[str] = None
    x_tvg_url: Optional[str] = None
    timeout_s: Optional[float] = None
    user_agent: Optional[str] = None
    download_logos: Optional[bool] = None
    localize_logos: Optional[bool] = None
    logo_skip_existing: Optional[bool] = None
    logo_dir: Optional[str] = None
    epg_out: Optional[str] = None
    epg_base_url: Optional[str] = None
    epg_riddle: Optional[str] = None
    epg_time_ms: Optional[str] = None
    epg_days_forward: Optional[int] = None
    epg_days_back: Optional[int] = None
    scheduler_mode: Optional[str] = None  # "interval" | "cron"
    scheduler_interval_hours: Optional[int] = None
    scheduler_interval_minutes: Optional[int] = None
    scheduler_cron_hour: Optional[str] = None
    scheduler_cron_minute: Optional[str] = None
    udpxy: Optional[UdpxyConfigResponse] = None  # UDPXY 配置
    catchup: Optional[CatchupConfigResponse] = None  # 回放配置


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    input_url: Optional[str] = None
    source_iface: Optional[str] = None
    local_iface: Optional[str] = None
    output_m3u: Optional[str] = None
    use_udpxy: Optional[bool] = None
    udpxy_base: Optional[str] = None
    x_tvg_url: Optional[str] = None
    timeout_s: Optional[float] = None
    user_agent: Optional[str] = None
    download_logos: Optional[bool] = None
    localize_logos: Optional[bool] = None
    logo_skip_existing: Optional[bool] = None
    logo_dir: Optional[str] = None
    epg_out: Optional[str] = None
    epg_base_url: Optional[str] = None
    epg_riddle: Optional[str] = None
    epg_time_ms: Optional[str] = None
    epg_days_forward: Optional[int] = None
    epg_days_back: Optional[int] = None
    scheduler_mode: Optional[str] = None
    scheduler_interval_hours: Optional[int] = None
    scheduler_interval_minutes: Optional[int] = None
    scheduler_cron_hour: Optional[str] = None
    scheduler_cron_minute: Optional[str] = None
    udpxy: Optional[UdpxyConfigUpdateRequest] = None  # UDPXY 配置更新
    catchup: Optional[Dict] = None  # 回放配置更新


class ConfigUpdateResponse(BaseModel):
    """配置更新响应"""
    ok: bool
    config: ConfigResponse

