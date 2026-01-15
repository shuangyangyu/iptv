#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志 API 测试
"""

from fastapi.testclient import TestClient

from iptv_sever.api.main import app

client = TestClient(app)


def test_get_logs():
    """测试获取日志列表"""
    response = client.get("/api/v1/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)


def test_get_logs_with_limit():
    """测试获取日志列表（带限制）"""
    response = client.get("/api/v1/logs?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert len(data["logs"]) <= 10


def test_clear_logs():
    """测试清空日志"""
    response = client.post("/api/v1/logs/clear")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


def test_get_logs_after_clear():
    """测试清空后获取日志"""
    # 先清空
    client.post("/api/v1/logs/clear")
    # 再获取
    response = client.get("/api/v1/logs")
    assert response.status_code == 200
    data = response.json()
    # 应该至少有一条"日志已清空"的日志
    assert "logs" in data

