#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置 API 测试
"""

from fastapi.testclient import TestClient

from iptv_sever.api.main import app

client = TestClient(app)


def test_get_config():
    """测试获取配置"""
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "input_url" in data
    assert "source_iface" in data


def test_update_config():
    """测试更新配置"""
    response = client.put(
        "/api/v1/config",
        json={"source_iface": "eth1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "config" in data

