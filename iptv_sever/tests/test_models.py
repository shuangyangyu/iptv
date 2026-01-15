#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pydantic 模型测试
"""

import pytest
from pydantic import ValidationError

from iptv_sever.api.models.status import StatusResponse, FileStatus
from iptv_sever.api.models.config import ConfigResponse, ConfigUpdateRequest
from iptv_sever.api.models.network import NetworkResponse
from iptv_sever.api.models.log import LogEntry, LogsResponse
from iptv_sever.api.models.cron import CronStatusResponse, CronSetupRequest
from iptv_sever.api.models.udpxy import UdpxyStatusResponse


def test_file_status():
    """测试 FileStatus 模型"""
    status = FileStatus(exists=True, size=100, mtime=1234567890)
    assert status.exists is True
    assert status.size == 100
    assert status.mtime == 1234567890


def test_status_response():
    """测试 StatusResponse 模型"""
    status = StatusResponse(
        m3u=FileStatus(exists=True, size=100, mtime=1234567890),
        epg=FileStatus(exists=True, size=200, mtime=1234567890),
        last_job="m3u",
        last_job_rc=0,
        last_job_at=1234567890
    )
    assert status.last_job == "m3u"
    assert status.last_job_rc == 0


def test_config_response():
    """测试 ConfigResponse 模型"""
    config = ConfigResponse(
        input_url="http://example.com",
        source_iface="eth1",
        output_m3u="test.m3u"
    )
    assert config.input_url == "http://example.com"
    assert config.source_iface == "eth1"


def test_config_update_request():
    """测试 ConfigUpdateRequest 模型"""
    request = ConfigUpdateRequest(source_iface="eth1")
    assert request.source_iface == "eth1"
    assert request.input_url is None  # 未设置的字段为 None


def test_network_response():
    """测试 NetworkResponse 模型"""
    network = NetworkResponse(
        interface="eth1",
        ip="192.168.1.1",
        gateway="192.168.1.254"
    )
    assert network.interface == "eth1"
    assert network.ip == "192.168.1.1"


def test_log_entry():
    """测试 LogEntry 模型"""
    log = LogEntry(ts=1234567890, level="INFO", msg="Test message")
    assert log.ts == 1234567890
    assert log.level == "INFO"
    assert log.msg == "Test message"


def test_logs_response():
    """测试 LogsResponse 模型"""
    logs = LogsResponse(logs=[
        LogEntry(ts=1234567890, level="INFO", msg="Test 1"),
        LogEntry(ts=1234567891, level="ERROR", msg="Test 2")
    ])
    assert len(logs.logs) == 2
    assert logs.logs[0].level == "INFO"


def test_cron_status_response():
    """测试 CronStatusResponse 模型"""
    cron = CronStatusResponse(
        enabled=True,
        cron_expr="0 */6 * * *",
        cron_cmd="/path/to/script"
    )
    assert cron.enabled is True
    assert cron.cron_expr == "0 */6 * * *"


def test_cron_setup_request():
    """测试 CronSetupRequest 模型"""
    request = CronSetupRequest(
        mode="interval",
        interval_hours=6
    )
    assert request.mode == "interval"
    assert request.interval_hours == 6


def test_udpxy_status_response():
    """测试 UdpxyStatusResponse 模型"""
    status = UdpxyStatusResponse(
        running=True,
        pid=12345,
        port=4022,
        bind_address="0.0.0.0",
        source_iface="eth1",
        max_connections=1000,
        connections=5,
        uptime=3600,
        available=True
    )
    assert status.running is True
    assert status.port == 4022
    assert status.available is True

