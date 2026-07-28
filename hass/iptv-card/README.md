# IPTV Control Card（Home Assistant）

对接本仓库 MQTT Discovery 实体的 Lovelace 自定义卡片。

## 安装

1. 复制到 HA 的 `www` 目录：

```bash
mkdir -p /config/www/iptv-card
cp hass/iptv-card/iptv-card.js /config/www/iptv-card/
```

2. **设置 → 仪表盘 → 三个点 → 资源**，添加：

| 项 | 值 |
|----|-----|
| URL | `/local/iptv-card/iptv-card.js` |
| 类型 | JavaScript 模块 |

3. 刷新浏览器缓存后，仪表盘添加卡片（手动 YAML）：

```yaml
type: custom:iptv-control-card
title: IPTV 241
prefix: iptv_241
show_urls: true
show_actions: true
```

## 配置项

| 字段 | 默认 | 说明 |
|------|------|------|
| `title` | `IPTV` | 卡片标题 |
| `prefix` | `iptv_241` | 实体 ID 前缀（对应 `mqtt.client_id: iptv-241`） |
| `show_urls` | `true` | 显示 TiviMate / APTV / EPG 链接 |
| `show_actions` | `true` | 显示 Create / Restart 按钮 |

## 依赖实体（由 IPTV Server MQTT Discovery 自动创建）

- `binary_sensor.{prefix}_health`
- `binary_sensor.{prefix}_udpxy_running`
- `binary_sensor.{prefix}_last_job_ok`
- `sensor.{prefix}_udpxy_connections`
- `sensor.{prefix}_m3u_mtime` / `m3u_url` / `m3u_aptv_url`
- `sensor.{prefix}_epg_mtime` / `epg_url`
- `button.{prefix}_generate` / `run_m3u` / `run_epg` / `run_logos` / `udpxy_restart`

在 HA 开发者工具 → 状态里确认实体 ID；若前缀不同，改卡片的 `prefix`。
