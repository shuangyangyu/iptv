# Docker Hub Secrets 设置指南

本指南说明如何在 GitHub 仓库中设置 Docker Hub Secrets，以便 GitHub Actions 可以自动构建并推送 Docker 镜像。

## 步骤 1: 创建 Docker Hub Access Token

1. 登录 Docker Hub：https://hub.docker.com
2. 点击右上角头像，选择 **Account Settings**
3. 在左侧菜单中点击 **Security**
4. 找到 **New Access Token** 部分
5. 点击 **Generate New Token** 按钮
6. 填写 Token 描述（例如：`GitHub Actions IPTV`）
7. 设置权限为 **Read, Write, Delete**
8. 点击 **Generate** 生成 Token
9. **重要**：复制 Token 并保存好，页面关闭后将无法再次查看

## 步骤 2: 在 GitHub 仓库中添加 Secrets

**方式一：使用 Repository secrets（推荐，更简单）**

1. 打开 GitHub 仓库：https://github.com/shuangyangyu/iptv
2. 点击仓库顶部的 **Settings** 标签
3. 在左侧菜单中找到 **Secrets and variables** → **Actions**
4. 点击 **New repository secret** 按钮（注意：是 Repository secrets，不是 Environment secrets）
5. 添加以下两个 Secrets：

**方式二：使用 Environment secrets（如果需要环境级别的管理）**

1. 打开 GitHub 仓库：https://github.com/shuangyangyu/iptv
2. 点击仓库顶部的 **Settings** 标签
3. 在左侧菜单中找到 **Environments**
4. 点击 **New environment** 创建新环境（例如：`production`）
5. 在环境设置中添加 Secrets：

### Secret 1: DOCKERHUB_USERNAME

- **Name**: `DOCKERHUB_USERNAME`
- **Value**: `shuangyangyu`（您的 Docker Hub 用户名）
- 点击 **Add secret**

### Secret 2: DOCKERHUB_TOKEN

- **Name**: `DOCKERHUB_TOKEN`
- **Value**: 粘贴您在步骤 1 中创建的 Access Token
- 点击 **Add secret**

**注意**：
- 如果使用 **Repository secrets**（方式一），直接在工作流中使用 `${{ secrets.DOCKERHUB_USERNAME }}`
- 如果使用 **Environment secrets**（方式二），需要：
  1. 在工作流文件中添加 `environment: production`（见 `.github/workflows/docker-build.yml`）
  2. 在 Environment 中添加 secrets，使用方式相同：`${{ secrets.DOCKERHUB_USERNAME }}`

## 步骤 3: 验证设置

1. 返回仓库主页
2. 点击 **Actions** 标签
3. 您应该能看到 **Docker Build and Push** 工作流
4. 推送到 `master` 分支或手动触发工作流来测试

## 工作流说明

工作流会在以下情况触发：
- 推送到 `master` 分支时自动触发
- 手动触发（在 Actions 页面点击 **Run workflow**）

工作流将执行以下操作：
1. 检出代码
2. 设置 Docker Buildx
3. 登录 Docker Hub
4. 构建并推送 `shuangyangyu/iptv-backend:latest` 镜像
5. 构建并推送 `shuangyangyu/iptv-frontend:latest` 镜像

## 镜像命名

推送的镜像：
- `shuangyangyu/iptv-backend:latest`
- `shuangyangyu/iptv-frontend:latest`

## 使用推送的镜像

在服务器上，可以使用以下命令拉取并使用镜像：

```bash
# 拉取镜像
docker pull shuangyangyu/iptv-backend:latest
docker pull shuangyangyu/iptv-frontend:latest

# 或者在 docker-compose.yml 中直接使用
services:
  backend:
    image: shuangyangyu/iptv-backend:latest
    # ...
  frontend:
    image: shuangyangyu/iptv-frontend:latest
    # ...
```

## 故障排除

### 问题 1: 构建失败 - "unauthorized: authentication required"

**原因**: Docker Hub Secrets 未正确设置

**解决**:
1. 检查 Secrets 名称是否正确（`DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN`）
2. 检查 Token 是否有效（Token 可能已过期或权限不足）
3. 重新创建 Token 并更新 Secret

### 问题 2: 推送失败 - "denied: requested access to the resource is denied"

**原因**: Docker Hub 用户名或镜像名称错误

**解决**:
1. 检查 `.github/workflows/docker-build.yml` 中的 `DOCKERHUB_USERNAME` 是否正确
2. 确认您在 Docker Hub 上有权限推送镜像

### 问题 3: 构建超时

**原因**: 后端镜像构建需要编译 udpxy，可能需要较长时间

**解决**:
1. GitHub Actions 免费版有 6 小时的超时限制，通常足够
2. 如果经常超时，可以考虑使用缓存优化构建速度

## 安全建议

1. **不要** 将 Docker Hub Token 提交到代码仓库
2. **定期** 轮换 Access Token（建议每 90 天）
3. **使用** 最小权限原则（只授予必要的权限）
4. **监控** Actions 日志，检查是否有异常活动
