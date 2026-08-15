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
    import threading

    action = (data.get("action") or "").strip().lower()
    name = (data.get("name") or "").strip().lower()
    svc = get_mqtt_service()

    # 一键生成：m3u（含 logo）+ epg（后台线程，避免阻塞 MQTT）
    if action in ("generate", "run_all") or (
        action == "job" and name in ("all", "generate", "full")
    ):
        logger.info("MQTT 一键生成：m3u + epg + logo")

        def _run_generate():
            try:
                r_m3u = execute_job(
                    "m3u",
                    overrides={"download_logos": True, "localize_logos": True},
                )
                r_epg = execute_job("epg")
                ok = bool(r_m3u.get("ok")) and bool(r_epg.get("ok"))
                publish_status_mqtt()
                if svc:
                    svc.publish(
                        "event",
                        {
                            "ok": ok,
                            "action": "generate",
                            "m3u": bool(r_m3u.get("ok")),
                            "epg": bool(r_epg.get("ok")),
                            "logo": bool(r_m3u.get("ok")),
                        },
                        retain=False,
                    )
                logger.info(
                    "一键生成结束 ok=%s m3u=%s epg=%s",
                    ok,
                    r_m3u.get("ok"),
                    r_epg.get("ok"),
                )
            except Exception as e:
                logger.error("一键生成失败: %s", e, exc_info=True)
                if svc:
                    svc.publish(
                        "event",
                        {"ok": False, "action": "generate", "error": str(e)},
                        retain=False,
                    )

        threading.Thread(target=_run_generate, name="iptv-generate", daemon=True).start()
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

    if action in ("diag", "network_diag", "check_network"):
        from .services.network_diag import run_network_diag

        result = run_network_diag()
        if svc:
            svc.publish("diag", result, retain=True)
            svc.publish(
                "event",
                {
                    "ok": bool(result.get("ok")),
                    "action": "diag",
                    "summary": result.get("summary"),
                },
                retain=False,
            )
        return

    raise ValueError(f"unknown action: {action}")


def _run_scheduled_jobs() -> None:
    from .services.job import execute_job

    logger.info("调度任务：开始 m3u + epg + logo")
    execute_job("m3u", overrides={"download_logos": True, "localize_logos": True})
    execute_job("epg")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_runtime_config()

    # udpxy：未运行则拉起；已运行但绑定旧专网 IP 则重绑
    try:
        from .services.udpxy import ensure_udpxy_bound_to_source_ip

        result = ensure_udpxy_bound_to_source_ip()
        logger.info(f"启动时 UDPXY 绑定检查: {result}")
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

    # scheduler：定时任务 + MQTT 状态定期刷新（连接数等）
    try:
        from .services.scheduler import start_scheduler
        from .services.state import publish_status_mqtt
        from .services.udpxy import ensure_udpxy_bound_to_source_ip

        start_scheduler(
            cfg,
            _run_scheduled_jobs,
            status_poll=publish_status_mqtt,
            status_interval_seconds=15,
            udpxy_watch=ensure_udpxy_bound_to_source_ip,
            udpxy_watch_seconds=30,
        )
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
        "endpoints": ["/health", "/diag", "/out/", "/catchup/"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/diag")
async def diag():
    """网络环境自检（双网卡 / 网关 / DNS / 频道源 / udpxy / 回看）。"""
    from .services.network_diag import get_last_diag, run_network_diag
    from iptv_sever.mqtt import get_mqtt_service

    result = run_network_diag()
    svc = get_mqtt_service()
    if svc:
        try:
            svc.publish("diag", result, retain=True)
        except Exception:
            pass
    # 附带上次结果字段，方便客户端对比
    if get_last_diag():
        pass
    return result


if __name__ == "__main__":
    import uvicorn

    host, port = get_http_bind()
    uvicorn.run(app, host=host, port=port)
