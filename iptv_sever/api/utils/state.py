#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
状态管理工具函数
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from ..config import STATE_PATH, logger


def now_ts() -> int:
    """获取当前时间戳"""
    return int(time.time())


def default_state() -> Dict[str, Any]:
    """返回默认状态配置"""
    return {
        "config": {
            "input_url": "http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js",
            "source_iface": "eth1",
            "output_m3u": "iptv.m3u",
            "use_udpxy": True,
            "udpxy_base": "http://192.168.1.250:4022",
            "x_tvg_url": "",
            "timeout_s": 10.0,
            "user_agent": "curl/8.0.0",
            "download_logos": True,
            "localize_logos": True,
            "logo_skip_existing": True,
            "epg_out": "epg.xml",
            "epg_base_url": "http://cms.99tv.com.cn:99/cms/liveVideoOtt_searchProgramList6p1.action",
            "epg_riddle": "0e5172956bf2c1d87381056eb23ebe5a",
            "epg_time_ms": "1764552092957",
            "epg_days_forward": 7,
            "epg_days_back": 0,
            "scheduler_mode": "interval",
            "scheduler_interval_hours": 6,
            "scheduler_interval_minutes": 0,
            "scheduler_cron_hour": "*/6",
            "scheduler_cron_minute": "0",
            "udpxy": {
                "enabled": True,
                "port": 4022,
                "bind_address": "0.0.0.0",
                "source_iface": "eth1",
                "max_connections": 5,
                "log_file": "/var/log/udpxy.log",
                "pid_file": "/tmp/udpxy.pid",
            },
            "catchup": {
                "target_host": "10.255.129.26",
                "target_port": 6060,
                "virtual_domain": "hls.tvod_hls.zte.com",
            },
        },
        "status": {
            "m3u": {"exists": False, "size": 0, "mtime": 0},
            "epg": {"exists": False, "size": 0, "mtime": 0},
            "last_job": "",
            "last_job_rc": None,
            "last_job_at": 0,
        },
        "logs": [],
    }


def load_state() -> Dict[str, Any]:
    """加载状态文件"""
    if not STATE_PATH.exists():
        return default_state()
    try:
        return json.loads(STATE_PATH.read_text("utf-8"))
    except Exception:
        return default_state()


def save_state(state: Dict[str, Any]) -> None:
    """保存状态文件"""
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_log(state: Dict[str, Any], level: str, msg: str) -> None:
    """追加日志"""
    logs: List[Dict[str, Any]] = state.setdefault("logs", [])
    logs.append({"ts": now_ts(), "level": level, "msg": msg})
    # 控制体积：只保留最后 400 条
    if len(logs) > 400:
        del logs[:-400]

