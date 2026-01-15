#!/bin/bash
# GitHub 仓库创建和推送脚本

set -e

echo "=== GitHub 仓库创建和推送脚本 ==="
echo ""

# 检查 GitHub CLI 是否已登录
if ! gh auth status &>/dev/null; then
    echo "❌ GitHub CLI 未登录"
    echo "请先运行: gh auth login"
    exit 1
fi

# 获取仓库名（从用户输入或使用默认值）
REPO_NAME=${1:-iptv}

echo "📦 仓库名: $REPO_NAME"
echo ""

# 检查是否已有远程仓库
if git remote get-url origin &>/dev/null; then
    echo "⚠️  已存在远程仓库 origin"
    read -p "是否要更新远程仓库 URL? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
    else
        echo "使用现有远程仓库"
        git push -u origin dev/v2.8
        git push -u origin master
        exit 0
    fi
fi

# 创建 GitHub 仓库
echo "🚀 正在创建 GitHub 仓库..."
gh repo create "$REPO_NAME" \
    --public \
    --source=. \
    --remote=origin \
    --description="IPTV 服务器管理系统 - 支持 M3U/EPG 生成、UDPXY 集成、Docker 部署"

echo ""
echo "✅ 仓库创建成功！"
echo ""

# 推送代码
echo "📤 正在推送代码..."
git push -u origin dev/v2.8
git push -u origin master

echo ""
echo "✅ 代码推送完成！"
echo ""
echo "🌐 仓库地址: https://github.com/$(gh api user --jq .login)/$REPO_NAME"
