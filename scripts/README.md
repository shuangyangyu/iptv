# 开发调试部署脚本

本目录包含所有用于开发调试和部署的脚本。

## 快速开始

### 首次使用

1. **配置 SSH 连接**（如果还没有）：
   ```bash
   ./scripts/setup_ssh.sh
   ```

2. **配置部署参数**：
   编辑 `scripts/config.sh`，设置服务器信息

3. **同步代码到服务器**：
   ```bash
   ./scripts/sync.sh all
   ```

4. **在服务器上准备环境**：
   ```bash
   ssh user@host 'bash ~/iptv_sever/setup_server.sh'
   ```

5. **在服务器上启动服务**：
   ```bash
   ssh user@host 'bash ~/iptv_sever/start.sh'
   ```

## 脚本列表

### 核心脚本

- **`config.sh`** - 统一配置文件（所有脚本都引用此文件）
- **`sync.sh`** - 基础同步脚本（从本地同步代码到服务器）

### 服务管理（服务器端脚本）

这些脚本需要先同步到服务器，然后在服务器上本地运行：

- **`server_start.sh`** - 启动服务脚本（同步后为 `start.sh`）
- **`server_stop.sh`** - 停止服务脚本（同步后为 `stop.sh`）
- **`server_restart.sh`** - 重启服务脚本（同步后为 `restart.sh`）
- **`server_status.sh`** - 状态检查脚本（同步后为 `status.sh`）

同步命令：`./scripts/sync.sh start_scripts`


## 使用示例

### 同步代码到服务器

```bash
./sync.sh              # 同步所有（包括 API、Backend、Tests、Frontend）
./sync.sh api          # 只同步 api 目录
./sync.sh backend      # 只同步 backend 目录
./sync.sh tests        # 只同步 tests 目录（测试文件）
./sync.sh frontend     # 只同步前端构建文件
```

### 查看服务状态（在服务器上）

```bash
# SSH 到服务器后运行
bash ~/iptv_sever/status.sh
```

### 查看日志（在服务器上）

```bash
# SSH 到服务器后运行
tail -f ~/iptv_sever/api.log
```

### 运行测试（在服务器上）

```bash
# SSH 到服务器后运行
cd ~/iptv_sever
source venv/bin/activate
pytest tests/ -v              # 运行所有测试
pytest tests/test_udpxy.py -v # 运行 UDPXY 测试
pytest tests/test_network.py -v # 运行网络接口测试
```

## 详细文档

详细使用说明请参考：[开发调试部署指南](../文档/开发调试部署指南.md)
