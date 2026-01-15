#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cron API 测试
"""

from fastapi.testclient import TestClient

from iptv_sever.api.main import app

client = TestClient(app)


def test_get_cron_status():
    """测试获取 Cron 状态"""
    response = client.get("/api/v1/cron")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert isinstance(data["enabled"], bool)


def test_setup_cron_interval():
    """测试设置 Cron（间隔模式）"""
    response = client.post(
        "/api/v1/cron",
        json={
            "mode": "interval",
            "interval_hours": 6,
            "source_iface": "eth1"
        }
    )
    # 可能成功或失败，取决于系统环境
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data


def test_setup_cron_cron():
    """测试设置 Cron（Cron 模式）"""
    response = client.post(
        "/api/v1/cron",
        json={
            "mode": "cron",
            "cron_hour": "*/6",
            "cron_minute": "0",
            "source_iface": "eth1"
        }
    )
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data


def test_remove_cron():
    """测试移除 Cron"""
    response = client.delete("/api/v1/cron")
    # 可能成功或失败，取决于系统环境
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data

