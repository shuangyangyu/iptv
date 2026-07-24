#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""进程内调度：按 YAML scheduler 跑 m3u/epg。"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:  # pragma: no cover
    BackgroundScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore
    IntervalTrigger = None  # type: ignore

_scheduler: Any = None
_lock = threading.Lock()


def start_scheduler(
    cfg: dict,
    run_jobs: Callable[[], None],
) -> None:
    """
    cfg: flatten runtime config（含 scheduler_*）
    run_jobs: 无参回调，通常跑 m3u 再 epg
    """
    global _scheduler
    mode = (cfg.get("scheduler_mode") or "off").strip().lower()
    if mode in ("", "off", "disabled", "none"):
        logger.info("调度器关闭 (scheduler.mode=off)")
        return
    if BackgroundScheduler is None:
        logger.error("未安装 APScheduler，无法启动调度")
        return

    with _lock:
        stop_scheduler()
        sched = BackgroundScheduler(timezone="Asia/Shanghai")
        if mode == "interval":
            hours = int(cfg.get("scheduler_interval_hours") or 0)
            minutes = int(cfg.get("scheduler_interval_minutes") or 0)
            if hours <= 0 and minutes <= 0:
                hours = 6
            sched.add_job(
                run_jobs,
                IntervalTrigger(hours=hours, minutes=minutes),
                id="iptv_jobs",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            logger.info(f"调度器 interval: every {hours}h {minutes}m")
        elif mode == "cron":
            hour = str(cfg.get("scheduler_cron_hour") or "*/6")
            minute = str(cfg.get("scheduler_cron_minute") or "0")
            sched.add_job(
                run_jobs,
                CronTrigger(hour=hour, minute=minute),
                id="iptv_jobs",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            logger.info(f"调度器 cron: {minute} {hour} * * *")
        else:
            logger.warning(f"未知 scheduler.mode={mode}，调度器未启动")
            return
        sched.start()
        _scheduler = sched

    if cfg.get("scheduler_run_on_startup"):
        threading.Thread(target=run_jobs, name="iptv-startup-jobs", daemon=True).start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
