#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IPTV Server：YAML 配置 + 管道 HTTP + MQTT/HA
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

if __package__ in (None, ""):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    iptv_sever_dir = os.path.dirname(script_dir)
    repo_root = os.path.dirname(iptv_sever_dir)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import OUT_DIR, logger
from .routers import catchup
from .settings import get_http_bind, get_runtime_config, reload_config


def _handle_mqtt_command(data: dict) -> None:
    from .services.job import execute_job
    from .services.state import publish_status_mqtt
    from .services import udpxy as udpxy_svc
    from iptv_sever.mqtt import get_mqtt_service

    action = (data.get("action") or "").strip().lower()
    name = (data.get("name") or "").strip().lower()
    svc = get_mqtt_service()

    # 一键生成：m3u + epg
    if action in ("generate", "run_all") or (
        action == "job" and name in ("all", "generate", "full")
    ):
        logger.info("MQTT 一键生成：m3u + epg")
        r_m3u = execute_job("m3u")
        r_epg = execute_job("epg")
        ok = bool(r_m3u.get("ok")) and bool(r_epg.get("ok"))
        if svc:
            svc.publish(
                "event",
                {
                    "ok": ok,
                    "action": "generate",
                    "m3u": bool(r_m3u.get("ok")),
                    "epg": bool(r_epg.get("ok")),
                },
                retain=False,
            )
        return

    if action == "job":
        result = execute_job(name)
        if svc:
            svc.publish(
                "event",
                {"ok": bool(result.get("ok")), "action": "job", "name": name},
                retain=False,
            )
        return

    if action == "udpxy":
        if name == "start":
            result = udpxy_svc.start_udpxy()
        elif name == "stop":
            result = udpxy_svc.stop_udpxy()
        elif name == "restart":
            result = udpxy_svc.restart_udpxy()
        else:
            raise ValueError(f"unknown udpxy action: {name}")
        publish_status_mqtt()
        if svc:
            svc.publish(
                "event",
                {
                    "ok": bool(result.get("ok")),
                    "action": "udpxy",
                    "name": name,
                    "message": result.get("message"),
                },
                retain=False,
            )
        return

    if action == "reload_config":
        reload_config()
        publish_status_mqtt()
        if svc:
            svc.publish("event", {"ok": True, "action": "reload_config"}, retain=False)
        return

    raise ValueError(f"unknown action: {action}")


def _run_scheduled_jobs() -> None:
    from .services.job import execute_job

    logger.info("调度任务：开始 m3u + epg")
    execute_job("m3u")
    execute_job("epg")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_runtime_config()

    # udpxy
    try:
        from .services.udpxy import get_udpxy_status, start_udpxy

        st = get_udpxy_status()
        if cfg.get("udpxy", {}).get("enabled", True) and not st.get("running"):
            result = start_udpxy()
            logger.info(f"启动时自动拉起 UDPXY: {result}")
        else:
            logger.info(f"UDPXY 状态: running={st.get('running')} pid={st.get('pid')}")
    except Exception as e:
        logger.error(f"启动 UDPXY 失败: {e}", exc_info=True)

    # mqtt
    try:
        from iptv_sever.mqtt import MqttService, set_mqtt_service
        from .services.state import publish_status_mqtt

        mqtt_svc = MqttService(cfg.get("mqtt") or {}, on_command=_handle_mqtt_command)
        set_mqtt_service(mqtt_svc)
        mqtt_svc.start()
        publish_status_mqtt()
    except Exception as e:
        logger.error(f"启动 MQTT 失败: {e}", exc_info=True)

    # scheduler
    try:
        from .services.scheduler import start_scheduler

        start_scheduler(cfg, _run_scheduled_jobs)
    except Exception as e:
        logger.error(f"启动调度器失败: {e}", exc_info=True)

    yield

    try:
        from .services.scheduler import stop_scheduler
        from iptv_sever.mqtt import get_mqtt_service, set_mqtt_service

        stop_scheduler()
        svc = get_mqtt_service()
        if svc:
            svc.stop()
        set_mqtt_service(None)
    except Exception:
        pass


app = FastAPI(
    title="IPTV Server",
    description="YAML 配置 + 管道 HTTP + MQTT/HA",
    version="3.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

OUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/out", StaticFiles(directory=str(OUT_DIR)), name="out")
logger.info(f"静态文件: /out -> {OUT_DIR}")

app.include_router(catchup.router)


@app.get("/")
async def root():
    return {
        "name": "IPTV Server",
        "version": "3.0.0",
        "endpoints": ["/health", "/out/", "/catchup/"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    host, port = get_http_bind()
    uvicorn.run(app, host=host, port=port)
