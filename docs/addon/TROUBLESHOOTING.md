# Home Assistant Addon 故障排查指南

## 常见问题

### 1. Git Clone SSL 错误

**错误信息：**
```
fatal: unable to access 'https://github.com/shuangyangyu/iptv/': 
OpenSSL SSL_read: OpenSSL/3.5.4: error:0A000126:SSL routines::unexpected eof while reading
```

**可能原因：**
- HA 设备网络连接不稳定
- GitHub 访问受限
- 防火墙或代理设置问题

**解决方案：**

1. **检查网络连接**
   ```bash
   # SSH 到 HA 设备后测试
   ping github.com
   curl -I https://github.com
   ```

2. **配置代理（如果需要）**
   - 在 HA 配置中设置 HTTP/HTTPS 代理
   - 或在 Supervisor 设置中配置代理

3. **等待重试**
   - SSL 错误可能是临时网络问题
   - 等待 5-10 分钟后重试

4. **删除并重新添加仓库**
   - Supervisor → Add-on Store → Repositories
   - 删除旧的仓库
   - 重新添加：`https://github.com/shuangyangyu/iptv`

### 2. 构建镜像失败

**错误信息：**
```
Failed to to call /addons/afe25d1e_iptv_server/install - 
An unknown error occurred while trying to build the image
```

**查看详细日志：**

1. **通过 SSH 访问 HA**
   ```bash
   ha supervisor logs | grep -A 50 "iptv_server\|build\|error"
   ```

2. **在 HA UI 中查看**
   - Supervisor → System
   - 查看日志或下载诊断信息

3. **通过终端查看**
   ```bash
   docker logs hassio_supervisor 2>&1 | grep -A 50 "iptv"
   ```

**常见构建错误：**

#### a) COPY 路径错误
```
lstat iptv_sever/api/requirements.txt: no such file or directory
```
**解决：** 检查文件是否存在，路径是否正确

#### b) 依赖安装失败
```
ERROR: Could not find a version that satisfies...
```
**解决：** 检查 `requirements.txt` 中的依赖版本

#### c) udpxy 编译失败
```
make: *** [udpxy] Error 1
```
**解决：** 已添加容错处理，允许继续构建

### 3. 仓库已存在错误

**错误信息：**
```
Can't add https://github.com/shuangyangyu/iptv, already in the store
```

**解决方案：**
1. Supervisor → Add-on Store → Repositories
2. 找到并删除旧的仓库
3. 重新添加仓库

## 诊断步骤

### 步骤 1：检查网络连接
```bash
# SSH 到 HA 设备
ping github.com
curl -I https://github.com/shuangyangyu/iptv
```

### 步骤 2：查看 Supervisor 日志
```bash
ha supervisor logs | grep -A 50 "iptv_server"
```

### 步骤 3：检查仓库结构
确保仓库包含以下文件：
- `repository.json` (在根目录)
- `addon/config.yaml`
- `addon/Dockerfile`
- `addon/run.sh`
- `iptv_sever/api/requirements.txt`
- `iptv_sever/api/` (目录)
- `iptv_sever/backend/` (目录)

### 步骤 4：测试本地构建（可选）
如果可能，在本地测试 Dockerfile：
```bash
cd /path/to/iptv
docker build -f addon/Dockerfile --build-arg BUILD_FROM=homeassistant/amd64-base:latest -t test-iptv .
```

## 获取帮助

如果问题仍然存在：

1. **收集信息：**
   - Supervisor 日志（`ha supervisor logs`）
   - HA 系统信息（Supervisor → System → System information）
   - 错误截图

2. **提交问题：**
   - GitHub Issues: https://github.com/shuangyangyu/iptv/issues
   - 包含详细的错误信息和日志

## 联系信息

- GitHub: https://github.com/shuangyangyu/iptv
- Issues: https://github.com/shuangyangyu/iptv/issues
