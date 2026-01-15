#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络接口 API 测试
"""

from fastapi.testclient import TestClient

from iptv_sever.api.main import app

client = TestClient(app)


def test_get_interfaces():
    """测试获取网络接口列表"""
    response = client.get("/api/v1/interfaces")
    assert response.status_code == 200
    data = response.json()
    assert "interfaces" in data
    assert isinstance(data["interfaces"], list)


def test_get_interfaces_physical():
    """测试获取物理网络接口列表"""
    response = client.get("/api/v1/interfaces?physical=true")
    assert response.status_code == 200
    data = response.json()
    assert "interfaces" in data
    assert "physical_only" in data
    assert data["physical_only"] is True
    assert isinstance(data["interfaces"], list)


def test_get_interface_detail():
    """测试获取网络接口详细信息"""
    # 先获取接口列表，然后测试第一个接口
    response = client.get("/api/v1/interfaces")
    assert response.status_code == 200
    data = response.json()
    interfaces = data.get("interfaces", [])
    
    if interfaces:
        # 使用第一个接口名称测试
        first_interface = interfaces[0].get("name") if isinstance(interfaces[0], dict) else interfaces[0]
        if first_interface:
            response = client.get(f"/api/v1/interfaces/{first_interface}")
            assert response.status_code == 200
            detail_data = response.json()
            assert "interfaces" in detail_data
            assert isinstance(detail_data["interfaces"], list)
