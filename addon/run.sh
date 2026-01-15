#!/usr/bin/sh
set -e

# Home Assistant Addon 启动脚本
# 从环境变量读取配置并启动服务

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

# 读取配置
API_PORT=${api_port:-8088}
UDPXY_PORT=${udpxy_port:-4022}
SOURCE_IFACE=${source_iface:-}
LOCAL_IFACE=${local_iface:-}
LOG_LEVEL=${log_level:-info}

# HA addon 数据目录
DATA_DIR="/data"
OUT_DIR="${DATA_DIR}/out"
STATE_FILE="${DATA_DIR}/state.json"
LOG_FILE="${DATA_DIR}/api.log"

# 创建必要的目录
mkdir -p "${OUT_DIR}" "${DATA_DIR}"

log "IPTV Server Addon 启动中..."
log "API 端口: ${API_PORT}"
log "UDPXY 端口: ${UDPXY_PORT}"
log "源网络接口: ${SOURCE_IFACE:-未配置}"
log "本地网络接口: ${LOCAL_IFACE:-未配置}"
log "日志级别: ${LOG_LEVEL}"

# 初始化或更新 state.json 配置
if [ ! -f "${STATE_FILE}" ]; then
    log "创建初始配置文件..."
    cat > "${STATE_FILE}" <<EOF
{
    "config": {
        "input_url": "http://yepg.99tv.com.cn:99/pic/channel/list/channel_5.js",
        "source_iface": "${SOURCE_IFACE}",
        "local_iface": "${LOCAL_IFACE}",
        "output_m3u": "iptv.m3u",
        "use_udpxy": true,
        "udpxy_base": "http://127.0.0.1:${UDPXY_PORT}",
        "x_tvg_url": "",
        "timeout_s": 10.0,
        "user_agent": "curl/8.0.0",
        "download_logos": true,
        "localize_logos": true,
        "logo_skip_existing": true,
        "epg_out": "epg.xml",
        "epg_base_url": "http://cms.99tv.com.cn:99/cms/liveVideoOtt_searchProgramList6p1.action",
        "epg_riddle": "0e5172956bf2c1d87381056eb23ebe5a",
        "epg_time_ms": "1764552092957",
        "epg_days_forward": 7,
        "epg_days_back": 0,
        "scheduler_mode": "interval",
        "scheduler_interval_hours": 6,
        "scheduler_interval_minutes": 0,
        "scheduler_cron_hour": "*/6",
        "scheduler_cron_minute": "0",
        "udpxy": {
            "enabled": true,
            "port": ${UDPXY_PORT},
            "bind_address": "0.0.0.0",
            "source_iface": "${SOURCE_IFACE}",
            "max_connections": 5,
            "log_file": "${DATA_DIR}/udpxy.log",
            "pid_file": "${DATA_DIR}/udpxy.pid"
        },
        "catchup": {
            "target_host": "10.255.129.26",
            "target_port": 6060,
            "virtual_domain": "hls.tvod_hls.zte.com"
        }
    },
    "status": {
        "m3u": {"exists": false, "size": 0, "mtime": 0},
        "epg": {"exists": false, "size": 0, "mtime": 0},
        "last_job": "",
        "last_job_rc": null,
        "last_job_at": 0
    },
    "logs": []
}
EOF
else
    log "更新现有配置文件..."
    # 使用 Python 更新配置（如果 Python 可用）
    python3 <<EOF 2>/dev/null || true
import json
import os

state_file = "${STATE_FILE}"
if os.path.exists(state_file):
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    # 更新网络接口配置
    if "${SOURCE_IFACE}":
        state['config']['source_iface'] = "${SOURCE_IFACE}"
        if 'udpxy' in state['config']:
            state['config']['udpxy']['source_iface'] = "${SOURCE_IFACE}"
    
    if "${LOCAL_IFACE}":
        state['config']['local_iface'] = "${LOCAL_IFACE}"
    
    # 更新 UDPXY 配置
    if 'udpxy' in state['config']:
        state['config']['udpxy']['port'] = ${UDPXY_PORT}
        state['config']['udpxy']['bind_address'] = "0.0.0.0"
        state['config']['udpxy']['log_file'] = "${DATA_DIR}/udpxy.log"
        state['config']['udpxy']['pid_file'] = "${DATA_DIR}/udpxy.pid"
    
    # 更新 UDPXY base URL
    state['config']['udpxy_base'] = "http://127.0.0.1:${UDPXY_PORT}"
    
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)
EOF
fi

# 设置环境变量供应用使用
export API_PORT="${API_PORT}"
export API_HOST="0.0.0.0"
export DATA_DIR="${DATA_DIR}"
export OUT_DIR="${OUT_DIR}"
export STATE_FILE="${STATE_FILE}"
export LOG_FILE="${LOG_FILE}"
export LOG_LEVEL="${LOG_LEVEL}"

# 信号处理函数
cleanup() {
    log "收到停止信号，正在关闭服务..."
    # 停止 UDPXY（如果正在运行）
    if [ -f "${DATA_DIR}/udpxy.pid" ]; then
        PID=$(cat "${DATA_DIR}/udpxy.pid" 2>/dev/null || echo "")
        if [ -n "${PID}" ]; then
            kill "${PID}" 2>/dev/null || true
        fi
    fi
    # 停止 Python 进程
    pkill -f "uvicorn.*iptv_sever.api.main" || true
    exit 0
}

trap cleanup SIGTERM SIGINT

# 启动 FastAPI 服务
log "启动 FastAPI 后端服务..."
cd /app
exec python3 -m uvicorn iptv_sever.api.main:app \
    --host 0.0.0.0 \
    --port "${API_PORT}" \
    --log-level "${LOG_LEVEL}" \
    &

# 等待服务启动
sleep 2

# 检查服务是否启动成功
if ! pgrep -f "uvicorn.*iptv_sever.api.main" > /dev/null; then
    log "错误: FastAPI 服务启动失败"
    exit 1
fi

log "FastAPI 服务已启动，监听端口 ${API_PORT}"

# 保持运行
wait
