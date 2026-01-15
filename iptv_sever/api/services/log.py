#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志服务
"""

from typing import Any, Dict, List

from ..utils.state import append_log, load_state, save_state


def get_logs(limit: int = 200) -> List[Dict[str, Any]]:
    """
    获取日志列表
    
    Args:
        limit: 返回的日志条数（1-400）
    
    Returns:
        日志列表（按时间倒序，最新的在前）
    """
    limit = max(1, min(400, limit))
    state = load_state()
    logs = state.get("logs", [])
    # 取最后 limit 条，然后反转以返回倒序（最新的在前）
    return list(reversed(logs[-limit:]))


def clear_logs() -> None:
    """清空日志"""
    state = load_state()
    state["logs"] = []
    save_state(state)
    append_log(state, "INFO", "日志已清空")

