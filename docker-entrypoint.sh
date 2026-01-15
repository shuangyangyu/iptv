#!/bin/bash
# Docker 容器启动脚本
# 启动 cron 服务和 FastAPI 服务

set -e

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "启动 IPTV 服务..."

# 启动 cron 服务（用于定时任务）
log "启动 cron 服务..."
service cron start || crond || true

# 等待 cron 启动
sleep 1

# 检查 cron 是否运行
if pgrep -x cron > /dev/null || pgrep -x crond > /dev/null; then
    log "✅ Cron 服务已启动"
else
    log "⚠️  Cron 服务启动失败，定时任务可能无法运行"
fi

# 启动 FastAPI 服务
log "启动 FastAPI 后端服务..."
exec python3 -m uvicorn iptv_sever.api.main:app \
    --host 0.0.0.0 \
    --port ${API_PORT:-8088}
