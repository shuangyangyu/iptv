# 解决 Git Clone SSL 错误

## 问题描述

```
fatal: unable to access 'https://github.com/shuangyangyu/iptv/': 
OpenSSL SSL_read: OpenSSL/3.5.4: error:0A000126:SSL routines::unexpected eof while reading
```

这是网络连接问题，导致 HA 无法从 GitHub 克隆仓库。

## 解决方案

### 方案 1：检查并修复网络连接

#### 1.1 检查网络连接

如果有 SSH 访问权限：

```bash
# SSH 到 HA 设备
ssh root@192.168.1.249

# 测试网络连接
ping github.com
curl -I https://github.com
```

#### 1.2 检查 DNS 解析

```bash
# 测试 DNS
nslookup github.com
dig github.com
```

#### 1.3 检查防火墙/代理

- 确保 HA 设备能访问互联网
- 检查防火墙规则
- 如果使用代理，需要在 HA 中配置

### 方案 2：配置 Git SSL 设置（临时方案）

**警告：** 这会降低安全性，仅用于诊断。

如果有 SSH 访问权限：

```bash
# SSH 到 HA 设备
ssh root@192.168.1.249

# 临时禁用 SSL 验证（仅用于诊断）
git config --global http.sslVerify false

# 测试克隆
git clone https://github.com/shuangyangyu/iptv.git /tmp/test-iptv

# 如果成功，重新启用 SSL 验证
git config --global http.sslVerify true
```

### 方案 3：使用代理（如果 HA 在受限网络中）

#### 3.1 在 HA 配置中设置代理

1. 进入 HA：设置 → 系统 → 网络
2. 配置 HTTP/HTTPS 代理
3. 保存并重启

#### 3.2 在 Supervisor 中配置代理

如果有 Supervisor 配置选项，可以在那里配置代理。

### 方案 4：等待并重试

SSL 错误可能是临时网络问题：
- 等待 10-30 分钟后重试
- 检查网络是否恢复正常

### 方案 5：直接使用 docker-compose（推荐）

如果网络问题持续，最简单的方法是直接使用 docker-compose：

```bash
# 在 HA 设备上
cd /path/to/iptv
docker-compose up -d
```

**优点：**
- 不需要通过 Supervisor 安装
- 不需要解决 Git clone 问题
- 功能完全相同
- 更简单直接

**步骤：**

1. **将代码复制到 HA 设备**
   ```bash
   # 在本地
   scp -r /path/to/iptv root@192.168.1.249:/opt/iptv
   
   # 或使用 rsync
   rsync -avz /path/to/iptv root@192.168.1.249:/opt/iptv
   ```

2. **在 HA 设备上启动**
   ```bash
   # SSH 到 HA 设备
   ssh root@192.168.1.249
   
   # 进入项目目录
   cd /opt/iptv
   
   # 启动服务
   docker-compose up -d
   ```

3. **访问服务**
   - 前端：http://192.168.1.249
   - 后端 API：http://192.168.1.249:8088
   - API 文档：http://192.168.1.249:8088/docs

## 推荐方案

**如果网络问题持续：**
- ✅ **直接使用 docker-compose**（最简单、最可靠）
- 功能完全相同
- 不需要解决 Git clone 问题
- 更容易维护和更新

**如果想继续使用 addon：**
- 先解决网络问题
- 确保能正常访问 GitHub
- 然后重新尝试安装

## 需要帮助？

如果选择使用 docker-compose，我可以帮你：
1. 创建部署脚本
2. 配置自动启动
3. 设置更新流程
