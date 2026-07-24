#!/bin/bash
# Docker 容器启动：单进程 FastAPI（内置 APScheduler + MQTT）

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "启动 IPTV Server..."
export CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"
export API_PORT="${API_PORT:-8088}"
export API_HOST="${API_HOST:-0.0.0.0}"

exec python3 -m uvicorn iptv_sever.api.main:app \
    --host "${API_HOST}" \
    --port "${API_PORT}"
