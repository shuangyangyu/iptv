# 测试套件说明

## 测试文件列表

### API 路由测试
- `test_status.py` - 状态 API 测试（1个测试）
- `test_config.py` - 配置 API 测试（2个测试）
- `test_network.py` - 网络接口 API 测试（3个测试）
- `test_jobs.py` - 任务执行 API 测试（4个测试）
- `test_logs.py` - 日志 API 测试（4个测试）
- `test_cron.py` - Cron API 测试（4个测试）
- `test_udpxy.py` - UDPXY API 测试（6个测试）
- `test_root.py` - 根路径和健康检查测试（2个测试）

### 服务层测试
- `test_services.py` - 服务层单元测试（10个测试）

### 模型测试
- `test_models.py` - Pydantic 模型测试（10个测试）

## 测试统计

**总计**: 46 个测试用例

| 模块 | 测试文件 | 测试数量 |
|------|---------|---------|
| 状态和配置 | test_status.py, test_config.py | 3 |
| 网络接口 | test_network.py | 3 |
| 任务执行 | test_jobs.py | 4 |
| 日志管理 | test_logs.py | 4 |
| 定时任务 | test_cron.py | 4 |
| UDPXY 管理 | test_udpxy.py | 6 |
| 根路径 | test_root.py | 2 |
| 服务层 | test_services.py | 10 |
| 数据模型 | test_models.py | 10 |

## 运行测试

### 运行所有测试

#### 本地环境
```bash
cd /Users/yushuangyang/Documents/dev/iptv/iptv_sever
source venv/bin/activate
pytest tests/ -v
```

#### 服务器环境
```bash
cd ~/iptv_sever
source venv/bin/activate
pytest tests/ -v
```

### 运行特定测试文件
```bash
pytest tests/test_status.py -v
pytest tests/test_config.py -v
pytest tests/test_network.py -v
pytest tests/test_udpxy.py -v
```

### 运行特定测试函数
```bash
pytest tests/test_status.py::test_get_status -v
```

### 生成测试覆盖率报告
```bash
pytest tests/ --cov=api --cov-report=html
```

## 测试覆盖范围

### API 端点覆盖
- ✅ GET /api/v1/status
- ✅ GET /api/v1/config
- ✅ PUT /api/v1/config
- ✅ GET /api/v1/interfaces
- ✅ GET /api/v1/interfaces/{name}
- ✅ POST /api/v1/jobs/{job_type}
- ✅ GET /api/v1/logs
- ✅ POST /api/v1/logs/clear
- ✅ GET /api/v1/cron
- ✅ POST /api/v1/cron
- ✅ DELETE /api/v1/cron
- ✅ GET /api/v1/udpxy
- ✅ POST /api/v1/udpxy/actions
- ✅ GET /api/v1/udpxy/config
- ✅ PUT /api/v1/udpxy/config
- ✅ GET /
- ✅ GET /health

### 服务层覆盖
- ✅ get_status()
- ✅ get_config()
- ✅ update_config()
- ✅ get_network_interfaces()
- ✅ get_interfaces_detail_info()
- ✅ get_logs()
- ✅ clear_logs()
- ✅ get_udpxy_status()
- ✅ get_udpxy_config()

### 数据模型覆盖
- ✅ FileStatus
- ✅ StatusResponse
- ✅ ConfigResponse
- ✅ ConfigUpdateRequest
- ✅ NetworkInterfacesResponse
- ✅ NetworkInterfaceDetailResponse
- ✅ LogEntry
- ✅ LogsResponse
- ✅ CronStatusResponse
- ✅ CronSetupRequest
- ✅ UdpxyStatusResponse
- ✅ UdpxyActionRequest
- ✅ UdpxyActionResponse

## 注意事项

1. **环境依赖**: 部分测试需要系统命令（如 `ip`, `crontab`），在非 Linux 环境可能失败
2. **网络测试**: 网络相关测试可能因为网络环境不同而结果不同
3. **UDPXY 测试**: UDPXY 相关测试需要系统安装 UDPXY 程序
4. **服务器测试**: 测试文件可以通过 `./scripts/sync.sh tests` 同步到服务器，在服务器上运行测试可以验证实际环境

## 修复的问题

- ✅ 修复 Pydantic V2 警告：使用 `model_dump()` 替代 `dict()`
- ✅ 更新 test_network.py：使用新的 `/api/v1/interfaces` 端点
- ✅ 更新 test_udpxy.py：使用新的 `/api/v1/udpxy` 和 `/api/v1/udpxy/actions` 端点
- ✅ 修复 test_services.py：使用 `get_network_interfaces()` 和 `get_interfaces_detail_info()` 替代已删除的 `get_network_info()`
- ✅ 添加所有 API 端点的测试
- ✅ 添加服务层单元测试
- ✅ 添加数据模型验证测试

## 同步到服务器

测试文件可以通过同步脚本同步到服务器：

```bash
# 同步所有代码（包括测试文件）
./scripts/sync.sh all

# 只同步测试文件
./scripts/sync.sh tests
```

在服务器上运行测试：```bash
ssh user@host 'cd ~/iptv_sever && source venv/bin/activate && pytest tests/ -v'
```
