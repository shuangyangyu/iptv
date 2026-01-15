#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
状态 API 测试
"""

from fastapi.testclient import TestClient

from iptv_sever.api.main import app

client = TestClient(app)


def test_get_status():
    """测试获取系统状态"""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "m3u" in data
    assert "epg" in data
    assert "last_job" in data

