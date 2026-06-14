# 诊断 SSL 问题（ping 能通但 SSL 失败）

## 问题现象

- ✅ `ping github.com` 能通
- ❌ `git clone https://github.com/...` SSL 错误
- ❌ `curl https://github.com` SSL 错误

## 诊断步骤

### 1. 测试 HTTPS 连接

在 HA 设备上运行（如果有 SSH 访问）：

```bash
# 测试 HTTPS 连接
curl -v https://github.com

# 测试特定仓库
curl -v https://github.com/shuangyangyu/iptv
```

查看输出中的 SSL 相关信息。

### 2. 检查 OpenSSL 版本

```bash
openssl version
```

### 3. 测试 SSL 连接

```bash
# 测试 SSL 连接
openssl s_client -connect github.com:443 -showcerts

# 查看详细的 SSL 信息
openssl s_client -connect github.com:443 -tls1_2
```

### 4. 检查 Git 配置

```bash
# 查看 Git SSL 配置
git config --global --get http.sslVerify
git config --global --get http.sslCAInfo

# 检查 Git 版本
git --version
```

## 解决方案

### 方案 1：更新 CA 证书

```bash
# 在 HA 设备上
apk update && apk add ca-certificates
# 或
apt-get update && apt-get install ca-certificates
```

### 方案 2：配置 Git 使用系统 CA 证书

```bash
# 在 HA 设备上
git config --global http.sslCAInfo /etc/ssl/certs/ca-certificates.crt
# 或（Alpine）
git config --global http.sslCAInfo /etc/ssl/certs/ca-bundle.crt
```

### 方案 3：临时禁用 SSL 验证（仅用于诊断）

**警告：** 这会降低安全性，仅用于诊断。

```bash
# 临时禁用
git config --global http.sslVerify false

# 测试克隆
git clone https://github.com/shuangyangyu/iptv /tmp/test

# 如果成功，重新启用
git config --global http.sslVerify true
```

### 方案 4：使用 SSH URL（如果配置了 SSH key）

如果 GitHub 配置了 SSH key，可以使用 SSH URL：

```
git@github.com:shuangyangyu/iptv.git
```

但 HA Supervisor 可能不支持 SSH URL。

### 方案 5：配置代理（如果使用代理）

如果 HA 在代理后面：

```bash
# 配置 Git 使用代理
git config --global http.proxy http://proxy:port
git config --global https.proxy https://proxy:port
```

### 方案 6：直接使用 docker-compose（推荐）

如果 SSL 问题持续，最简单的方法是直接使用 docker-compose：

```bash
# 使用部署脚本
./deploy_to_ha.sh
```

功能完全相同，不需要通过 Supervisor。

## 常见原因

### 1. CA 证书过期或不完整

**症状：** SSL 握手失败，证书验证错误

**解决：** 更新 CA 证书

### 2. TLS 版本不兼容

**症状：** 连接被拒绝或握手失败

**解决：** 更新 OpenSSL 或 Git

### 3. 防火墙/代理干扰

**症状：** 连接中断或超时

**解决：** 检查防火墙规则，配置代理

### 4. 时间不同步

**症状：** 证书验证失败（证书过期）

**解决：** 同步系统时间

```bash
# 检查时间
date

# 同步时间（如果可能）
ntpdate -s time.nist.gov
```

## 诊断命令汇总

在 HA 设备上运行以下命令进行诊断：

```bash
# 1. 测试网络连接
ping -c 3 github.com

# 2. 测试 HTTPS
curl -v https://github.com 2>&1 | grep -i ssl

# 3. 测试 SSL 连接
openssl s_client -connect github.com:443 < /dev/null 2>&1 | head -20

# 4. 检查 Git 配置
git config --global --list | grep ssl

# 5. 检查系统时间
date

# 6. 检查 OpenSSL 版本
openssl version
```

## 推荐方案

如果 SSL 问题持续存在，**强烈推荐使用 docker-compose 直接部署**：

1. ✅ 不需要解决 SSL 问题
2. ✅ 功能完全相同
3. ✅ 更容易维护
4. ✅ 可以随时更新

使用部署脚本：
```bash
./deploy_to_ha.sh
```
