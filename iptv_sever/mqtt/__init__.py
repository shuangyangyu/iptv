#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""MQTT 服务：状态推送、HA Discovery、命令订阅。"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover
    mqtt = None  # type: ignore


CmdHandler = Callable[[Dict[str, Any]], None]


class MqttService:
    def __init__(self, cfg: Dict[str, Any], on_command: Optional[CmdHandler] = None):
        self.cfg = dict(cfg or {})
        self.on_command = on_command
        self._client: Any = None
        self._connected = False
        self._lock = threading.RLock()
        self.prefix = (self.cfg.get("topic_prefix") or "iptv").rstrip("/")
        self.discovery_prefix = (
            self.cfg.get("discovery_prefix") or "homeassistant"
        ).rstrip("/")
        self.client_id = self.cfg.get("client_id") or "iptv-server"
        self.device_name = self.cfg.get("device_name") or "IPTV Server"

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("enabled"))

    def topic(self, *parts: str) -> str:
        return "/".join([self.prefix, *[p.strip("/") for p in parts if p]])

    def start(self) -> None:
        if not self.enabled:
            logger.info("MQTT 未启用")
            return
        if mqtt is None:
            logger.error("未安装 paho-mqtt，无法启动 MQTT")
            return
        host = self.cfg.get("host") or "127.0.0.1"
        port = int(self.cfg.get("port") or 1883)
        self._client = mqtt.Client(
            client_id=self.client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
        )
        username = self.cfg.get("username") or ""
        password = self.cfg.get("password") or ""
        if username:
            self._client.username_pw_set(username, password or None)

        self._client.will_set(
            self.topic("health"),
            payload="offline",
            qos=1,
            retain=True,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        try:
            self._client.connect_async(host, port, keepalive=60)
            self._client.loop_start()
            logger.info(f"MQTT 正在连接 {host}:{port} prefix={self.prefix}")
        except Exception as e:
            logger.error(f"MQTT 连接失败: {e}", exc_info=True)

    def stop(self) -> None:
        if not self._client:
            return
        try:
            self.publish("health", "offline", retain=True, raw=True)
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass
        self._client = None
        self._connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.error(f"MQTT 连接被拒 rc={rc}")
            self._connected = False
            return
        self._connected = True
        cmd_topic = self.topic("cmd")
        client.subscribe(cmd_topic, qos=1)
        logger.info(f"MQTT 已连接，订阅 {cmd_topic}")
        self.publish("health", "online", retain=True, raw=True)
        try:
            self.publish_discovery()
        except Exception as e:
            logger.error(f"发布 HA Discovery 失败: {e}", exc_info=True)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f"MQTT 断开 rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="replace").strip()
            data = json.loads(payload) if payload else {}
            if not isinstance(data, dict):
                raise ValueError("cmd payload must be object")
        except Exception as e:
            logger.warning(f"忽略非法 MQTT 命令: {e}")
            self.publish(
                "event",
                {"ok": False, "error": f"invalid cmd: {e}"},
                retain=False,
            )
            return
        if self.on_command:
            try:
                self.on_command(data)
            except Exception as e:
                logger.error(f"执行 MQTT 命令失败: {e}", exc_info=True)
                self.publish(
                    "event",
                    {"ok": False, "error": str(e), "cmd": data},
                    retain=False,
                )

    def publish(
        self,
        subtopic: str,
        payload: Any,
        *,
        retain: bool = True,
        raw: bool = False,
    ) -> None:
        if not self._client:
            return
        topic = self.topic(subtopic)
        if raw:
            body = payload if isinstance(payload, (bytes, bytearray)) else str(payload)
        else:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            try:
                self._client.publish(topic, body, qos=1, retain=retain)
            except Exception as e:
                logger.debug(f"MQTT publish 失败 {topic}: {e}")

    def _device(self) -> Dict[str, Any]:
        return {
            "identifiers": [self.client_id],
            "name": self.device_name,
            "manufacturer": "iptv",
            "model": "iptv-server",
            "sw_version": "3.0.0",
        }

    def _disc(
        self,
        component: str,
        object_id: str,
        payload: Dict[str, Any],
    ) -> None:
        topic = f"{self.discovery_prefix}/{component}/{self.client_id}/{object_id}/config"
        body = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            if self._client:
                self._client.publish(topic, body, qos=1, retain=True)

    def publish_discovery(self) -> None:
        avail = {
            "topic": self.topic("health"),
            "payload_available": "online",
            "payload_not_available": "offline",
        }
        device = self._device()
        # binary sensors
        self._disc(
            "binary_sensor",
            "health",
            {
                "name": "IPTV Health",
                "unique_id": f"{self.client_id}_health",
                "state_topic": self.topic("health"),
                "payload_on": "online",
                "payload_off": "offline",
                "device_class": "connectivity",
                "device": device,
            },
        )
        self._disc(
            "binary_sensor",
            "udpxy_running",
            {
                "name": "IPTV UDPXY Running",
                "unique_id": f"{self.client_id}_udpxy_running",
                "state_topic": self.topic("udpxy"),
                "value_template": "{{ 'ON' if value_json.running else 'OFF' }}",
                "availability": [avail],
                "device": device,
            },
        )
        self._disc(
            "binary_sensor",
            "last_job_ok",
            {
                "name": "IPTV Last Job OK",
                "unique_id": f"{self.client_id}_last_job_ok",
                "state_topic": self.topic("job"),
                "value_template": "{{ 'ON' if value_json.rc == 0 else 'OFF' }}",
                "availability": [avail],
                "device": device,
            },
        )
        # 清除旧 Size 实体（空 retain 删除 Discovery）
        for stale in ("m3u_size", "epg_size"):
            topic = (
                f"{self.discovery_prefix}/sensor/{self.client_id}/{stale}/config"
            )
            with self._lock:
                if self._client:
                    self._client.publish(topic, "", qos=1, retain=True)

        # sensors：mtime 日/月/年；输出路径用 download_url
        mtime_tpl = (
            "{% if value_json.mtime %}"
            "{{ value_json.mtime | int | timestamp_custom('%d/%m/%Y %H:%M', true) }}"
            "{% else %}—{% endif %}"
        )
        url_tpl = (
            "{% if value_json.download_url %}"
            "{{ value_json.download_url }}"
            "{% else %}—{% endif %}"
        )
        for key, name, template in (
            ("m3u_mtime", "IPTV M3U MTime", mtime_tpl),
            ("m3u_url", "IPTV M3U URL", url_tpl),
            ("epg_mtime", "IPTV EPG MTime", mtime_tpl),
            ("epg_url", "IPTV EPG URL", url_tpl),
        ):
            src = "m3u" if key.startswith("m3u") else "epg"
            self._disc(
                "sensor",
                key,
                {
                    "name": name,
                    "unique_id": f"{self.client_id}_{key}",
                    "state_topic": self.topic(src),
                    "value_template": template,
                    "availability": [avail],
                    "device": device,
                },
            )

        self._disc(
            "sensor",
            "udpxy_connections",
            {
                "name": "IPTV UDPXY Connections",
                "unique_id": f"{self.client_id}_udpxy_connections",
                "state_topic": self.topic("udpxy"),
                "value_template": "{{ value_json.connections }}",
                "availability": [avail],
                "device": device,
            },
        )
        self._disc(
            "sensor",
            "udpxy_uptime",
            {
                "name": "IPTV UDPXY Uptime",
                "unique_id": f"{self.client_id}_udpxy_uptime",
                "state_topic": self.topic("udpxy"),
                "value_template": "{{ value_json.uptime }}",
                "unit_of_measurement": "s",
                "availability": [avail],
                "device": device,
            },
        )
        # buttons -> publish to cmd
        for object_id, name, cmd in (
            ("run_m3u", "IPTV Run M3U", {"action": "job", "name": "m3u"}),
            ("run_epg", "IPTV Run EPG", {"action": "job", "name": "epg"}),
            ("run_logos", "IPTV Run Logos", {"action": "job", "name": "logos"}),
            (
                "udpxy_restart",
                "IPTV Restart UDPXY",
                {"action": "udpxy", "name": "restart"},
            ),
        ):
            self._disc(
                "button",
                object_id,
                {
                    "name": name,
                    "unique_id": f"{self.client_id}_{object_id}",
                    "command_topic": self.topic("cmd"),
                    "payload_press": json.dumps(cmd, separators=(",", ":")),
                    "availability": [avail],
                    "device": device,
                },
            )
        logger.info("已发布 Home Assistant MQTT Discovery")


_service: Optional[MqttService] = None


def get_mqtt_service() -> Optional[MqttService]:
    return _service


def set_mqtt_service(svc: Optional[MqttService]) -> None:
    global _service
    _service = svc


def publish_all_status(status: Dict[str, Any]) -> None:
    svc = get_mqtt_service()
    if not svc or not svc.enabled:
        return
    svc.publish("status", status, retain=True)
    if "m3u" in status:
        svc.publish("m3u", status["m3u"], retain=True)
    if "epg" in status:
        svc.publish("epg", status["epg"], retain=True)
    if "udpxy" in status:
        svc.publish("udpxy", status["udpxy"], retain=True)
    job = {
        "type": status.get("last_job") or "",
        "rc": status.get("last_job_rc"),
        "at": status.get("last_job_at") or 0,
    }
    svc.publish("job", job, retain=True)
    svc.publish("health", "online", retain=True, raw=True)
