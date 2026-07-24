#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
运行时状态（内存）：不再把配置写入 state.json。
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

_lock = threading.RLock()
_status: Dict[str, Any] = {
    "m3u": {"exists": False, "size": 0, "mtime": 0},
    "epg": {"exists": False, "size": 0, "mtime": 0},
    "last_job": "",
    "last_job_rc": None,
    "last_job_at": 0,
}
_logs: List[Dict[str, Any]] = []
_MAX_LOGS = 200


def now_ts() -> int:
    return int(time.time())


def get_runtime_status() -> Dict[str, Any]:
    with _lock:
        return {
            "m3u": dict(_status.get("m3u") or {}),
            "epg": dict(_status.get("epg") or {}),
            "last_job": _status.get("last_job", ""),
            "last_job_rc": _status.get("last_job_rc"),
            "last_job_at": _status.get("last_job_at", 0),
        }


def update_job_result(job_type: str, rc: Optional[int]) -> None:
    with _lock:
        _status["last_job"] = job_type
        _status["last_job_rc"] = rc
        _status["last_job_at"] = now_ts()


def update_file_status(kind: str, meta: Dict[str, Any]) -> None:
    with _lock:
        if kind in ("m3u", "epg"):
            _status[kind] = dict(meta)


def append_runtime_log(level: str, msg: str) -> None:
    with _lock:
        _logs.append({"ts": now_ts(), "level": level, "msg": msg})
        if len(_logs) > _MAX_LOGS:
            del _logs[:-_MAX_LOGS]


def get_runtime_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with _lock:
        return list(_logs[-limit:])
