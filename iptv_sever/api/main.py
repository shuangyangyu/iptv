#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FastAPI 应用入口
"""

import os
import sys
from pathlib import Path

# 允许两种运行方式
if __package__ in (None, ""):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    iptv_sever_dir = os.path.dirname(script_dir)
    repo_root = os.path.dirname(iptv_sever_dir)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import OUT_DIR, logger

# 创建 FastAPI 应用
app = FastAPI(
    title="IPTV Server API",
    description="IPTV M3U/EPG 生成服务 API",
    version="2.8.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置静态文件服务（/out 目录）
if OUT_DIR.exists():
    app.mount("/out", StaticFiles(directory=str(OUT_DIR)), name="out")
    logger.info(f"静态文件服务已挂载: /out -> {OUT_DIR}")
else:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/out", StaticFiles(directory=str(OUT_DIR)), name="out")
    logger.info(f"创建并挂载静态文件目录: /out -> {OUT_DIR}")

# 导入并注册路由
from .routers import catchup, config, cron, interfaces, jobs, logs, status, system, udpxy

app.include_router(status.router)
app.include_router(config.router)
app.include_router(interfaces.router)
app.include_router(jobs.router)
app.include_router(logs.router)
app.include_router(cron.router)
app.include_router(system.router)
app.include_router(catchup.router)
app.include_router(udpxy.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "IPTV Server API",
        "version": "2.8.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)

