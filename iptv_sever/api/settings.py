#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从 YAML 加载配置，并展平为与历史 get_config() 兼容的字典。
"""

from __future__ import annotations

import copy
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .config import logger

_lock = threading.RLock()
_cached: Optional[Dict[str, Any]] = None
_raw_cached: Optional[Dict[str, Any]] = None


def config_path() -> Path:
    env = os.environ.get("CONFIG_PATH", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    # 仓库根 / 容器 /app/config.yaml
    api_dir = Path(__file__).resolve().parent
    repo_root = api_dir.parent.parent
    for candidate in (
        Path("/app/config.yaml"),
        repo_root / "config.yaml",
        api_dir / "config.yaml",
    ):
        if candidate.exists():
            return candidate.resolve()
    return (repo_root / "config.yaml").resolve()


def default_yaml() -> Dict[str, Any]:
    return {
        "local_iface": "ens160",
        "source_iface": "ens192",
        "input_url": "http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js",
        "http": {"host": "0.0.0.0", "port": 8088},
        "output": {
            "m3u": "iptv.m3u",
            "m3u_aptv": "iptv-aptv.m3u",
            "catchup_style": "both",  # tivimate | aptv | both
            "epg": "epg.xml",
            "download_logos": True,
            "localize_logos": True,
            "logo_skip_existing": True,
        },
        "timeout_s": 10.0,
        "user_agent": "curl/8.0.0",
        "udpxy": {
            "enabled": True,
            "port": 4022,
            "bind_address": "0.0.0.0",
            "max_connections": 5,
            "log_file": "/var/log/udpxy.log",
            "pid_file": "/tmp/udpxy.pid",
        },
        "catchup": {
            "target_host": "10.255.129.26",
            "target_port": 6060,
            "virtual_domain": "hls.tvod_hls.zte.com",
        },
        "epg": {
            "base_url": "http://cms.99tv.com.cn:99/cms/liveVideoOtt_searchProgramList6p1.action",
            "riddle": "",
            "time_ms": "",
            "days_forward": 7,
            "days_back": 0,
        },
        "scheduler": {
            "mode": "interval",
            "interval_hours": 6,
            "interval_minutes": 0,
            "cron_hour": "*/6",
            "cron_minute": "0",
            "run_on_startup": False,
        },
        "mqtt": {
            "enabled": False,
            "host": "127.0.0.1",
            "port": 1883,
            "username": "",
            "password": "",
            "topic_prefix": "iptv",
            "discovery_prefix": "homeassistant",
            "client_id": "iptv-server",
            "device_name": "IPTV Server",
        },
    }


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _apply_env_overrides(raw: Dict[str, Any]) -> Dict[str, Any]:
    """允许用环境变量覆盖敏感项。"""
    mqtt = raw.setdefault("mqtt", {})
    if os.environ.get("MQTT_HOST"):
        mqtt["host"] = os.environ["MQTT_HOST"]
    if os.environ.get("MQTT_PORT"):
        mqtt["port"] = int(os.environ["MQTT_PORT"])
    if os.environ.get("MQTT_USERNAME"):
        mqtt["username"] = os.environ["MQTT_USERNAME"]
    if os.environ.get("MQTT_PASSWORD"):
        mqtt["password"] = os.environ["MQTT_PASSWORD"]
    if os.environ.get("MQTT_ENABLED"):
        mqtt["enabled"] = os.environ["MQTT_ENABLED"].strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
    http = raw.setdefault("http", {})
    if os.environ.get("API_HOST"):
        http["host"] = os.environ["API_HOST"]
    if os.environ.get("API_PORT"):
        http["port"] = int(os.environ["API_PORT"])
    return raw


def load_raw(force: bool = False) -> Dict[str, Any]:
    global _raw_cached
    with _lock:
        if _raw_cached is not None and not force:
            return copy.deepcopy(_raw_cached)
        path = config_path()
        raw = default_yaml()
        if path.exists():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if not isinstance(data, dict):
                    raise ValueError("config root must be a mapping")
                raw = _deep_merge(raw, data)
                logger.info(f"已加载配置: {path}")
            except Exception as e:
                logger.error(f"读取配置失败 {path}: {e}", exc_info=True)
                raise
        else:
            logger.warning(f"配置文件不存在，使用默认值: {path}")
        raw = _apply_env_overrides(raw)
        _validate(raw)
        _raw_cached = raw
        return copy.deepcopy(raw)


def _validate(raw: Dict[str, Any]) -> None:
    if not raw.get("input_url"):
        raise ValueError("config.input_url 必填")
    if not raw.get("local_iface"):
        raise ValueError("config.local_iface 必填")
    if not raw.get("source_iface"):
        raise ValueError("config.source_iface 必填")
    mqtt = raw.get("mqtt") or {}
    if mqtt.get("enabled") and not mqtt.get("host"):
        raise ValueError("mqtt.enabled 时必须设置 mqtt.host")


def flatten_runtime_config(raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    展平为历史 API/job 使用的扁平 config：
    output_m3u / epg_* / scheduler_* / udpxy / catchup 等。
    """
    raw = raw if raw is not None else load_raw()
    out = raw.get("output") or {}
    epg = raw.get("epg") or {}
    sched = raw.get("scheduler") or {}
    http = raw.get("http") or {}
    udpxy = copy.deepcopy(raw.get("udpxy") or {})
    catchup = copy.deepcopy(raw.get("catchup") or {})
    mqtt = copy.deepcopy(raw.get("mqtt") or {})

    # udpxy.source_iface 与顶层同步
    udpxy["source_iface"] = raw.get("source_iface") or udpxy.get("source_iface")

    flat: Dict[str, Any] = {
        "local_iface": raw.get("local_iface"),
        "source_iface": raw.get("source_iface"),
        "input_url": raw.get("input_url"),
        "output_m3u": out.get("m3u", "iptv.m3u"),
        "output_m3u_aptv": out.get("m3u_aptv", "iptv-aptv.m3u"),
        "catchup_style": out.get("catchup_style", "both"),
        "epg_out": out.get("epg", "epg.xml"),
        "download_logos": bool(out.get("download_logos", True)),
        "localize_logos": bool(out.get("localize_logos", True)),
        "logo_skip_existing": bool(out.get("logo_skip_existing", True)),
        "timeout_s": float(raw.get("timeout_s", 10.0)),
        "user_agent": raw.get("user_agent") or "curl/8.0.0",
        "use_udpxy": True,
        "udpxy": udpxy,
        "catchup": catchup,
        "epg_base_url": epg.get("base_url", ""),
        "epg_riddle": epg.get("riddle", ""),
        "epg_time_ms": str(epg.get("time_ms", "")),
        "epg_days_forward": int(epg.get("days_forward", 7)),
        "epg_days_back": int(epg.get("days_back", 0)),
        "scheduler_mode": sched.get("mode", "interval"),
        "scheduler_interval_hours": int(sched.get("interval_hours", 6)),
        "scheduler_interval_minutes": int(sched.get("interval_minutes", 0)),
        "scheduler_cron_hour": str(sched.get("cron_hour", "*/6")),
        "scheduler_cron_minute": str(sched.get("cron_minute", "0")),
        "scheduler_run_on_startup": bool(sched.get("run_on_startup", False)),
        "http_host": http.get("host", "0.0.0.0"),
        "http_port": int(http.get("port", 8088)),
        "mqtt": mqtt,
        "x_tvg_url": None,
    }
    return flat


def get_runtime_config(force: bool = False) -> Dict[str, Any]:
    global _cached
    with _lock:
        if _cached is not None and not force:
            return copy.deepcopy(_cached)
        raw = load_raw(force=force)
        _cached = flatten_runtime_config(raw)
        return copy.deepcopy(_cached)


def reload_config() -> Dict[str, Any]:
    return get_runtime_config(force=True)


def get_mqtt_config() -> Dict[str, Any]:
    return copy.deepcopy(get_runtime_config().get("mqtt") or {})


def get_http_bind() -> tuple[str, int]:
    cfg = get_runtime_config()
    return str(cfg.get("http_host") or "0.0.0.0"), int(cfg.get("http_port") or 8088)
