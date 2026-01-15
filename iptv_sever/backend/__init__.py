"""
iptv_sever.backend

这个目录用于放"本机侧"的 IPTV 工具代码（不依赖 OpenWrt）。

约定：
- `conf.py`：集中放默认值/常用配置项（便于后续统一调整）
- `core.py`：纯逻辑实现（加载频道、抽取频道、生成 M3U 等）
- `build_m3u.py`：命令行入口（第一阶段：把直播 M3U 跑通）
"""


