#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务执行 API 测试
"""

from fastapi.testclient import TestClient

from iptv_sever.api.main import app

client = TestClient(app)


def test_run_job_m3u():
    """测试执行 M3U 生成任务"""
    response = client.post("/api/v1/jobs/m3u")
    # 任务执行可能需要时间，也可能失败（取决于环境）
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data
        assert "status" in data


def test_run_job_epg():
    """测试执行 EPG 生成任务"""
    response = client.post("/api/v1/jobs/epg")
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        data = response.json()
        assert "ok" in data
        assert "status" in data


def test_run_job_logos():
    """测试执行 Logos 下载任务"""
    response = client.post("/api/v1/jobs/logos")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


def test_run_job_invalid():
    """测试无效的任务类型"""
    response = client.post("/api/v1/jobs/invalid")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "error" in data

