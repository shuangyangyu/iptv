#!/bin/bash
# 检查网络并推送代码

echo "=== 检查网络连接 ==="
echo ""

echo "1. 检查 GitHub 连接..."
if ping -c 3 github.com &>/dev/null; then
    echo "✅ GitHub 连接正常"
else
    echo "❌ 无法连接到 GitHub"
    exit 1
fi

echo ""
echo "2. 检查 GitHub CLI 状态..."
gh auth status

echo ""
echo "3. 检查远程仓库..."
git remote -v

echo ""
echo "4. 开始推送 dev/v2.8 分支..."
git push -u origin dev/v2.8

if [ $? -eq 0 ]; then
    echo "✅ dev/v2.8 推送成功！"
else
    echo "❌ dev/v2.8 推送失败"
    exit 1
fi

echo ""
echo "5. 开始推送 master 分支..."
git push -u origin master

if [ $? -eq 0 ]; then
    echo "✅ master 推送成功！"
    echo ""
    echo "🎉 所有分支推送完成！"
    echo "🌐 仓库地址: https://github.com/shuangyangyu/iptv"
else
    echo "❌ master 推送失败"
    exit 1
fi
