# GitHub 推送说明

## 仓库地址
https://github.com/shuangyangyu/iptv.git

## 推送方法

### 方法 1：使用 GitHub CLI（推荐）

```bash
# 1. 登录 GitHub CLI
gh auth login

# 2. 推送代码
git push -u origin dev/v2.8
git push -u origin master
```

### 方法 2：使用 HTTPS + Personal Access Token

1. 在 GitHub 创建 Personal Access Token:
   - 访问: https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择权限: repo (全部权限)
   - 复制生成的 token

2. 推送代码（使用 token 作为密码）:
```bash
git push -u origin dev/v2.8
# 用户名: shuangyangyu
# 密码: 粘贴你的 Personal Access Token
```

### 方法 3：使用 GitHub Desktop

1. 下载 GitHub Desktop: https://desktop.github.com/
2. 登录你的 GitHub 账号
3. 添加本地仓库
4. 推送代码

## 当前状态

- ✅ 远程仓库已配置
- ✅ 代码已准备好推送
- ⏳ 等待认证后推送

## 推送的分支

- dev/v2.8 (当前开发分支)
- master (主分支)
