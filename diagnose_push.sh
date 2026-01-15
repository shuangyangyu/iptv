#!/bin/bash
echo "=== 诊断推送问题 ==="
echo ""

echo "1. 检查 Git 配置:"
git config --list | grep -E "(user|remote|credential)" | head -10
echo ""

echo "2. 检查远程仓库:"
git remote -v
echo ""

echo "3. 检查 GitHub CLI 状态:"
gh auth status 2>&1
echo ""

echo "4. 检查仓库是否存在:"
gh repo view shuangyangyu/iptv 2>&1 | head -5
echo ""

echo "5. 检查本地分支:"
git branch
echo ""

echo "6. 检查提交历史:"
git log --oneline -3
echo ""

echo "=== 诊断完成 ==="
