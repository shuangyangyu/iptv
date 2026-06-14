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
# 使用 resolve() 确保所有路径都是绝对路径。
API_DIR = Path(__file__).resolve().parent
IPTV_SEVER_DIR = API_DIR.parent.resolve()
OUT_DIR = (IPTV_SEVER_DIR / "out").resolve()
STATE_PATH = (API_DIR / "state.json").resolve()
LOG_FILE = (API_DIR / "api.log").resolve()

# 配置日志
log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}
log_level_value = log_level_map.get(log_level, logging.DEBUG)

handlers = [logging.StreamHandler()]
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
handlers.append(logging.FileHandler(LOG_FILE, encoding='utf-8'))

logging.basicConfig(
    level=log_level_value,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

