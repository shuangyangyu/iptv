#!/bin/bash
# Docker 容器启动脚本
# 启动 cron 服务和 FastAPI 服务

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "启动 IPTV 服务..."

# 启动 cron 服务（用于定时任务）
# 即使失败也不影响 FastAPI 启动
log "启动 cron 服务..."
if command -v service > /dev/null; then
    service cron start 2>/dev/null || true
elif command -v crond > /dev/null; then
    crond -f -l 2 &
else
    log "⚠️  未找到 cron 服务，定时任务可能无法运行"
fi

# 等待 cron 启动
sleep 1

# 检查 cron 是否运行
if pgrep -x cron > /dev/null || pgrep -x crond > /dev/null; then
    log "✅ Cron 服务已启动"
else
    log "⚠️  Cron 服务启动失败，定时任务可能无法运行（不影响 API 服务）"
fi

# 启动 FastAPI 服务（使用 exec 确保成为主进程）
log "启动 FastAPI 后端服务..."
exec python3 -m uvicorn iptv_sever.api.main:app \
    --host 0.0.0.0 \
    --port ${API_PORT:-8088}
