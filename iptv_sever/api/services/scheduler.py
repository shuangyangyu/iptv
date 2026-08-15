#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""进程内调度：定时生成 m3u/epg + 定期刷新 MQTT 状态。"""

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
    *,
    status_poll: Optional[Callable[[], None]] = None,
    status_interval_seconds: int = 15,
    udpxy_watch: Optional[Callable[[], None]] = None,
    udpxy_watch_seconds: int = 30,
) -> None:
    """
    始终启动调度器：
    - 可选定时 m3u/epg
    - 可选定期 status_poll（推 MQTT，刷新 udpxy connections）
    - 可选 udpxy_watch（专网 DHCP 换地址后重绑组播）
    """
    global _scheduler
    if BackgroundScheduler is None:
        logger.error("未安装 APScheduler，无法启动调度")
        return

    mode = (cfg.get("scheduler_mode") or "off").strip().lower()

    with _lock:
        stop_scheduler()
        sched = BackgroundScheduler(timezone="Asia/Shanghai")

        if status_poll is not None:
            secs = max(5, int(status_interval_seconds or 15))
            sched.add_job(
                status_poll,
                IntervalTrigger(seconds=secs),
                id="iptv_mqtt_status",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            logger.info(f"MQTT 状态刷新: every {secs}s")

        if udpxy_watch is not None:
            watch_secs = max(15, int(udpxy_watch_seconds or 30))
            sched.add_job(
                udpxy_watch,
                IntervalTrigger(seconds=watch_secs),
                id="iptv_udpxy_rebind",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            logger.info(f"UDPXY 地址看守: every {watch_secs}s")

        if mode in ("", "off", "disabled", "none"):
            logger.info("任务调度关闭 (scheduler.mode=off)")
        elif mode == "interval":
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
            logger.info(f"任务调度 interval: every {hours}h {minutes}m")
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
            logger.info(f"任务调度 cron: {minute} {hour} * * *")
        else:
            logger.warning(f"未知 scheduler.mode={mode}，仅保留状态刷新")

        sched.start()
        _scheduler = sched

    if mode not in ("", "off", "disabled", "none") and cfg.get(
        "scheduler_run_on_startup"
    ):
        threading.Thread(target=run_jobs, name="iptv-startup-jobs", daemon=True).start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
