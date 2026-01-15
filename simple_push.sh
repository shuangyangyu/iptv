#!/bin/bash
# 简单的推送脚本

echo "🚀 开始推送代码..."
echo ""

# 使用 HTTPS 方式推送
git remote set-url origin https://github.com/shuangyangyu/iptv.git

echo "📤 推送 dev/v2.8 分支..."
git push -u origin dev/v2.8

echo ""
echo "📤 推送 master 分支..."
git push -u origin master

echo ""
echo "✅ 完成！"
