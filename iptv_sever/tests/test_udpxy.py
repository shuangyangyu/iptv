#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDPXY API 测试
"""

from fastapi.testclient import TestClient

from iptv_sever.api.main import app

client = TestClient(app)


def test_get_udpxy_status():
    """测试获取 UDPXY 状态"""
    response = client.get("/api/v1/udpxy")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert "port" in data
    assert "available" in data
    assert isinstance(data["running"], bool)
    assert isinstance(data["available"], bool)


def test_get_udpxy_config():
    """测试获取 UDPXY 配置"""
    response = client.get("/api/v1/udpxy/config")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "port" in data
    assert "bind_address" in data
    assert "source_iface" in data


def test_start_udpxy():
    """测试启动 UDPXY"""
    response = client.post("/api/v1/udpxy/actions", json={"action": "start"})
    # 可能成功或失败，取决于 UDPXY 是否安装
    assert response.status_code in [200, 400, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data
        assert "running" in data
        assert "message" in data


def test_stop_udpxy():
    """测试停止 UDPXY"""
    response = client.post("/api/v1/udpxy/actions", json={"action": "stop"})
    assert response.status_code in [200, 400, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data
        assert "running" in data
        assert "message" in data


def test_restart_udpxy():
    """测试重启 UDPXY"""
    response = client.post("/api/v1/udpxy/actions", json={"action": "restart"})
    assert response.status_code in [200, 400, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data
        assert "running" in data
        assert "message" in data


def test_update_udpxy_config():
    """测试更新 UDPXY 配置"""
    response = client.put(
        "/api/v1/udpxy/config",
        json={
            "port": 4022,
            "source_iface": "eth1"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "config" in data
