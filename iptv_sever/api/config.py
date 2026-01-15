#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI 配置模块
"""

import logging
import os
import sys
from pathlib import Path

# 允许两种运行方式：
# 1) 在仓库根目录：python3 -m iptv_sever.api.main
# 2) 直接跑脚本文件：python3 iptv_sever/api/main.py
if __package__ in (None, ""):
    script_dir = os.path.dirname(os.path.abspath(__file__))  # /www/iptv_sever/api
    iptv_sever_dir = os.path.dirname(script_dir)  # /www/iptv_sever
    repo_root = os.path.dirname(iptv_sever_dir)  # /www/
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

# 路径配置
API_DIR = Path(__file__).resolve().parent  # /www/iptv_sever/api
IPTV_SEVER_DIR = API_DIR.parent  # /www/iptv_sever
OUT_DIR = IPTV_SEVER_DIR / "out"  # /www/iptv_sever/out
STATE_PATH = API_DIR / "state.json"  # 状态文件位于 api 目录
LOG_FILE = API_DIR / "api.log"

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

