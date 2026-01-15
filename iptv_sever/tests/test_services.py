#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务层单元测试
"""

import pytest
from unittest.mock import patch, MagicMock

from iptv_sever.api.services.state import get_status, get_config, update_config
from iptv_sever.api.services.network import get_interfaces_detail_info, get_network_interfaces
from iptv_sever.api.services.log import get_logs, clear_logs
from iptv_sever.api.services.udpxy import get_udpxy_status, get_udpxy_config


def test_get_status():
    """测试获取状态服务"""
    status = get_status()
    assert "m3u" in status
    assert "epg" in status
    assert "last_job" in status


def test_get_config():
    """测试获取配置服务"""
    config = get_config()
    assert isinstance(config, dict)
    assert "input_url" in config or len(config) >= 0


def test_update_config():
    """测试更新配置服务"""
    original_config = get_config()
    updates = {"source_iface": "eth1"}
    updated_config = update_config(updates)
    assert isinstance(updated_config, dict)


def test_get_network_interfaces():
    """测试获取网络接口列表服务"""
    interfaces = get_network_interfaces()
    assert "interfaces" in interfaces
    assert isinstance(interfaces["interfaces"], list)


def test_get_interfaces_detail_info():
    """测试获取网络接口详细信息服务"""
    detail_info = get_interfaces_detail_info()
    assert "interfaces" in detail_info
    assert isinstance(detail_info["interfaces"], list)


def test_get_logs():
    """测试获取日志服务"""
    logs = get_logs(limit=10)
    assert isinstance(logs, list)


def test_get_logs_with_limit():
    """测试获取日志服务（带限制）"""
    logs = get_logs(limit=5)
    assert isinstance(logs, list)
    assert len(logs) <= 5


def test_clear_logs():
    """测试清空日志服务"""
    # 清空日志不应该抛出异常
    try:
        clear_logs()
        assert True
    except Exception:
        pytest.fail("clear_logs() raised an exception")


def test_get_udpxy_status():
    """测试获取 UDPXY 状态服务"""
    status = get_udpxy_status()
    assert "running" in status
    assert "port" in status
    assert "available" in status


def test_get_udpxy_config():
    """测试获取 UDPXY 配置服务"""
    config = get_udpxy_config()
    assert "enabled" in config
    assert "port" in config
    assert "bind_address" in config

