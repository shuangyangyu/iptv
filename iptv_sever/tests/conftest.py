#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pytest 配置和 fixtures
"""

import pytest
from fastapi.testclient import TestClient

from iptv_sever.api.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)

