#!/bin/bash
# 自动测试脚本 - 测试服务可访问性

echo "=========================================="
echo "IPTV Server 访问测试"
echo "=========================================="
echo ""

# 尝试从配置文件读取服务器地址
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/scripts/config.sh"

if [ -f "$CONFIG_FILE" ]; then
    # 从配置文件读取 SSH_HOST（通常是服务器 IP）
    source "$CONFIG_FILE"
    SERVER_IP="${SSH_HOST:-192.168.1.241}"
else
    # 默认值
    SERVER_IP="192.168.1.241"
fi

SERVER_PORT="8088"
BASE_URL="http://${SERVER_IP}:${SERVER_PORT}"

echo "服务器地址: ${SERVER_IP}:${SERVER_PORT}"
echo ""

# 测试函数
test_endpoint() {
    local endpoint=$1
    local name=$2
    local url="${BASE_URL}${endpoint}"
    
    echo "测试: ${name}"
    echo "URL: ${url}"
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${url}" 2>/dev/null)
    connect_time=$(curl -s -o /dev/null -w "%{time_connect}" --connect-timeout 5 "${url}" 2>/dev/null)
    total_time=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout 5 "${url}" 2>/dev/null)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "301" ] || [ "$http_code" = "302" ]; then
        echo "✅ 成功 - HTTP ${http_code} (连接: ${connect_time}s, 总计: ${total_time}s)"
        return 0
    elif [ -n "$http_code" ]; then
        echo "❌ 失败 - HTTP ${http_code}"
        return 1
    else
        echo "❌ 失败 - 无法连接"
        return 1
    fi
    echo ""
}

# 执行测试
echo "1. 测试健康检查端点 (/health)"
test_endpoint "/health" "健康检查"
echo ""

echo "2. 测试 API 文档端点 (/docs)"
test_endpoint "/docs" "API 文档"
echo ""

echo "3. 测试 API 根端点 (/)"
test_endpoint "/" "API 根"
echo ""

echo "4. 测试状态端点 (/api/v1/status)"
test_endpoint "/api/v1/status" "状态端点"
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "如果所有测试都成功，但 Chrome 浏览器仍无法访问，"
echo "请在 Chrome 中执行以下操作："
echo ""
echo "1. 清除 HSTS 设置："
echo "   chrome://net-internals/#hsts"
echo "   删除域名：${SERVER_IP}"
echo ""
echo "2. 清除 DNS 缓存："
echo "   chrome://net-internals/#dns"
echo "   点击 'Clear host cache'"
echo ""
echo "3. 使用无痕模式测试："
echo "   Ctrl+Shift+N (Windows) 或 Cmd+Shift+N (Mac)"
echo ""
