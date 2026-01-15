# Changelog

所有重要的变更都会记录在这个文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [2.8.0] - 2024-01-XX

### 新增
- 初始 Home Assistant addon 版本
- 支持通过 HA Supervisor 安装和管理
- 支持从环境变量读取配置
- 适配 HA addon 的数据目录结构（/data）
- 支持双网卡配置（source_iface 和 local_iface）
- 内置 UDPXY 服务支持
- 完整的 REST API 接口

### 技术细节
- 使用 host 网络模式以支持多网卡
- 需要 NET_ADMIN 和 NET_RAW 权限
- 数据持久化在 /data 目录
- 日志输出到标准输出（HA 自动捕获）

## [未发布]

### 计划
- 支持更多架构（armhf, armv7, aarch64, amd64, i386）
- 优化启动脚本
- 添加健康检查端点
- 改进错误处理和日志记录
