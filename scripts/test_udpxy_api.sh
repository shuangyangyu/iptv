#!/bin/bash
# -*- coding: utf-8 -*-
#
# UDPXY API 测试脚本

set -e

API_URL="http://localhost:8088/api/v1/udpxy"

echo "=========================================="
echo "UDPXY API 测试"
echo "=========================================="
echo ""

# 检查 API 服务是否运行
echo "1. 检查 API 服务..."
if ! pgrep -f 'uvicorn.*api.main:app' > /dev/null; then
    echo "   [错误] API 服务未运行"
    echo "   请先启动 API 服务:"
    echo "   cd ~/iptv_sever && source venv/bin/activate"
    echo "   uvicorn api.main:app --host 0.0.0.0 --port 8088"
    exit 1
fi
echo "   [成功] API 服务运行中"
echo ""

# 测试状态
echo "2. 测试 GET /udpxy/status"
echo "   请求: curl $API_URL/status"
response=$(curl -s "$API_URL/status" 2>&1)
echo "   响应:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
echo ""

# 测试停止
echo "3. 测试 POST /udpxy/stop"
echo "   请求: curl -X POST $API_URL/stop"
response=$(curl -s -X POST "$API_URL/stop" 2>&1)
echo "   响应:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
sleep 2
echo ""

# 测试启动
echo "4. 测试 POST /udpxy/start"
echo "   请求: curl -X POST $API_URL/start"
response=$(curl -s -X POST "$API_URL/start" 2>&1)
echo "   响应:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
sleep 2
echo ""

# 再次查看状态
echo "5. 再次查看状态"
echo "   请求: curl $API_URL/status"
response=$(curl -s "$API_URL/status" 2>&1)
echo "   响应:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
echo ""

# 测试重启
echo "6. 测试 POST /udpxy/restart"
echo "   请求: curl -X POST $API_URL/restart"
response=$(curl -s -X POST "$API_URL/restart" 2>&1)
echo "   响应:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
sleep 2
echo ""

# 最终状态
echo "7. 最终状态"
echo "   请求: curl $API_URL/status"
response=$(curl -s "$API_URL/status" 2>&1)
echo "   响应:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
echo ""

# 验证进程
echo "8. 验证 UDPXY 进程"
pgrep -af udpxy || echo "   未找到 UDPXY 进程"
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
