#!/bin/bash
# 推送代码到 GitHub

echo "🚀 开始推送代码到 GitHub..."
echo ""

# 推送 dev/v2.8 分支
echo "📤 推送 dev/v2.8 分支..."
git push -u origin dev/v2.8

if [ $? -eq 0 ]; then
    echo "✅ dev/v2.8 分支推送成功！"
else
    echo "❌ dev/v2.8 分支推送失败"
    exit 1
fi

echo ""

# 推送 master 分支
echo "📤 推送 master 分支..."
git push -u origin master

if [ $? -eq 0 ]; then
    echo "✅ master 分支推送成功！"
else
    echo "❌ master 分支推送失败"
    exit 1
fi

echo ""
echo "🎉 所有分支推送完成！"
echo "🌐 仓库地址: https://github.com/shuangyangyu/iptv"
