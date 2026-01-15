#!/bin/bash
# API 服务状态检查脚本

echo "=========================================="
echo "API 服务状态检查"
echo "=========================================="
echo ""

# 检查进程
echo "[1] 检查 API 服务进程..."
API_PID=$(pgrep -f 'uvicorn.*api.main:app')
if [ -z "$API_PID" ]; then
    echo "❌ API 服务未运行"
    echo ""
    echo "请运行以下命令启动服务："
    echo "  cd ~/iptv_sever"
    echo "  bash start.sh"
    exit 1
else
    echo "✅ API 服务正在运行 (PID: $API_PID)"
fi
echo ""

# 检查端口
echo "[2] 检查端口 8088 监听状态..."
PORT_STATUS=$(ss -tlnp 2>/dev/null | grep ':8088 ' || netstat -tlnp 2>/dev/null | grep ':8088 ')
if [ -z "$PORT_STATUS" ]; then
    echo "❌ 端口 8088 未监听"
else
    echo "✅ 端口 8088 正在监听"
    echo "   详情: $PORT_STATUS"
fi
echo ""

# 检查日志
echo "[3] 检查最近的日志（最后 20 行）..."
if [ -f ~/iptv_sever/api.log ]; then
    echo "--- 日志文件: ~/iptv_sever/api.log ---"
    tail -20 ~/iptv_sever/api.log
    echo ""
else
    echo "⚠️  日志文件不存在: ~/iptv_sever/api.log"
    echo ""
fi

# 检查错误
echo "[4] 检查最近的错误..."
if [ -f ~/iptv_sever/api.log ]; then
    ERROR_COUNT=$(grep -i "error\|exception\|traceback\|failed" ~/iptv_sever/api.log | tail -5 | wc -l)
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "⚠️  发现最近的错误/异常："
        grep -i "error\|exception\|traceback\|failed" ~/iptv_sever/api.log | tail -5
        echo ""
    else
        echo "✅ 未发现最近的错误"
    fi
else
    echo "⚠️  无法检查错误（日志文件不存在）"
fi
echo ""

# 测试连接
echo "[5] 测试本地连接..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 本地连接正常 (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "000" ]; then
    echo "❌ 无法连接到服务器（curl 失败）"
else
    echo "⚠️  连接异常 (HTTP $HTTP_CODE)"
fi
echo ""

echo "=========================================="
echo "检查完成"
echo "=========================================="
