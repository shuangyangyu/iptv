#!/bin/bash
# -*- coding: utf-8 -*-

"""
使用Linux cron设置EPG定时更新任务

这是更简单、更可靠的方式，利用Linux系统自带的cron服务。
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_EPG_SCRIPT="${SCRIPT_DIR}/build_epg.py"
CRON_JOB_NAME="iptv_epg_update"
CRON_FILE="/tmp/${CRON_JOB_NAME}.cron"

# 检查脚本是否存在
if [ ! -f "$BUILD_EPG_SCRIPT" ]; then
    echo "错误: 找不到EPG构建脚本: $BUILD_EPG_SCRIPT"
    exit 1
fi

# 默认配置
INTERVAL_HOURS="${1:-6}"  # 默认每6小时执行一次
SOURCE_IFACE="${2:-eth1}"  # 默认网卡

# 解析参数
MODE="interval"
CRON_HOUR="*/${INTERVAL_HOURS}"
CRON_MINUTE="0"

while [[ $# -gt 0 ]]; do
    case $1 in
        --interval-hours)
            INTERVAL_HOURS="$2"
            CRON_HOUR="*/${INTERVAL_HOURS}"
            shift 2
            ;;
        --cron-hour)
            CRON_HOUR="$2"
            MODE="cron"
            shift 2
            ;;
        --cron-minute)
            CRON_MINUTE="$2"
            MODE="cron"
            shift 2
            ;;
        --source-iface)
            SOURCE_IFACE="$2"
            shift 2
            ;;
        --remove)
            # 移除cron任务
            echo "正在移除cron任务..."
            crontab -l 2>/dev/null | grep -v "${BUILD_EPG_SCRIPT}" | crontab - || true
            echo "✓ cron任务已移除"
            exit 0
            ;;
        --list)
            # 列出当前cron任务
            echo "当前的EPG更新cron任务:"
            crontab -l 2>/dev/null | grep "${BUILD_EPG_SCRIPT}" || echo "未找到相关任务"
            exit 0
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --interval-hours N    每N小时执行一次（默认: 6）"
            echo "  --cron-hour H         Cron小时表达式（例如: '*/6' 或 '2,14'）"
            echo "  --cron-minute M       Cron分钟表达式（默认: '0'）"
            echo "  --source-iface IFACE  指定网卡（默认: eth1）"
            echo "  --remove              移除cron任务"
            echo "  --list                列出当前cron任务"
            echo "  --help                显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 --interval-hours 6              # 每6小时执行一次"
            echo "  $0 --cron-hour '*/4' --cron-minute '0'  # 每4小时执行一次"
            echo "  $0 --cron-hour '2' --cron-minute '0'   # 每天凌晨2点执行"
            echo "  $0 --remove                         # 移除任务"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# 构建cron表达式和命令
CRON_EXPR="${CRON_MINUTE} ${CRON_HOUR} * * *"
CRON_CMD="cd ${SCRIPT_DIR} && /usr/bin/python3 ${BUILD_EPG_SCRIPT} --source-iface ${SOURCE_IFACE} >/tmp/iptv_epg_update.log 2>&1"

# 移除旧任务（如果存在）
echo "正在设置cron任务..."
crontab -l 2>/dev/null | grep -v "${BUILD_EPG_SCRIPT}" | crontab - || true

# 添加新任务
(crontab -l 2>/dev/null; echo "${CRON_EXPR} ${CRON_CMD}") | crontab -

echo "✓ cron任务已设置"
echo ""
echo "Cron表达式: ${CRON_EXPR}"
echo "执行命令: ${CRON_CMD}"
echo ""
echo "查看日志: tail -f /tmp/iptv_epg_update.log"
echo "查看cron任务: crontab -l"
echo "移除任务: $0 --remove"

