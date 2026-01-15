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
# 支持 Home Assistant addon 环境（使用 /data 目录）
# 如果 DATA_DIR 环境变量存在且是绝对路径，使用 HA addon 的数据目录
DATA_DIR = Path(os.environ.get("DATA_DIR", ""))
if DATA_DIR and DATA_DIR.is_absolute() and DATA_DIR.exists():
    # HA addon 环境
    API_DIR = Path(__file__).resolve().parent  # /app/iptv_sever/api
    IPTV_SEVER_DIR = API_DIR.parent.resolve()  # /app/iptv_sever (确保是绝对路径)
    OUT_DIR = Path(os.environ.get("OUT_DIR", str(DATA_DIR / "out"))).resolve()  # /data/out (确保是绝对路径)
    STATE_PATH = Path(os.environ.get("STATE_FILE", str(DATA_DIR / "state.json"))).resolve()  # /data/state.json
    LOG_FILE = Path(os.environ.get("LOG_FILE", str(DATA_DIR / "api.log"))).resolve()  # /data/api.log
else:
    # 标准环境
    # 使用 resolve() 确保所有路径都是绝对路径
    API_DIR = Path(__file__).resolve().parent  # /app/iptv_sever/api
    IPTV_SEVER_DIR = API_DIR.parent.resolve()  # /app/iptv_sever (确保是绝对路径)
    OUT_DIR = (IPTV_SEVER_DIR / "out").resolve()  # /app/iptv_sever/out (确保是绝对路径)
    STATE_PATH = (API_DIR / "state.json").resolve()  # 状态文件位于 api 目录
    LOG_FILE = (API_DIR / "api.log").resolve()

# 配置日志
# 支持从环境变量读取日志级别（HA addon 环境）
log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}
log_level_value = log_level_map.get(log_level, logging.DEBUG)

# 在 HA addon 环境中，日志主要输出到标准输出（HA 会捕获）
# 文件日志作为补充
handlers = [logging.StreamHandler()]
if DATA_DIR and DATA_DIR.exists():
    # HA addon 环境：确保日志目录存在
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(LOG_FILE, encoding='utf-8'))
else:
    # 标准环境：同时输出到文件和控制台
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(LOG_FILE, encoding='utf-8'))

logging.basicConfig(
    level=log_level_value,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

