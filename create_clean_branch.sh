#!/bin/bash
# 创建干净的推送分支

echo "=== 创建干净的推送分支 ==="
echo ""

# 创建新的孤立分支
git checkout --orphan clean-main

# 添加所有当前文件
git add -A

# 创建初始提交
git commit -m "Initial commit: IPTV Server Management System

- FastAPI backend with UDPXY integration
- Vue.js frontend
- Docker support
- M3U/EPG generation
- Catchup support"

echo ""
echo "✅ 干净分支创建完成！"
echo ""
echo "📋 下一步："
echo "  1. 推送到新分支: git push -u origin clean-main"
echo "  2. 或者推送到 master: git push -u origin clean-main:master --force"
echo ""
