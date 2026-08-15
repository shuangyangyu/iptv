# IPTV Server

YAML 配置 + 直播 udpxy + 回看反代 + MQTT / Home Assistant Discovery。

不再提供 Web 管理 UI。播放器只访问局域网 HTTP；状态与按钮走 MQTT。

## 快速开始

```bash
cp config.example.yaml config.yaml
# 编辑 local_iface / source_iface / mqtt.host 等

docker compose up -d
```

对外端口（host 网络）：

| 端口 | 用途 |
|------|------|
| 8088 | `/out` m3u/epg、`/catchup` 回看、`/health`、`/diag` |
| 4022 | udpxy 直播 |

专网口 `source_iface` 走 DHCP 时地址会变。进程每 30 秒对照当前 IP 与 udpxy `/status` 的 Multicast address，不一致则自动重启（冷却 60 秒）。`/health` 仍可能为 ok，黑屏时看 `/diag` 的 `udpxy_bind_ip`。

播放列表：
- TiviMate：`http://<lan-ip>:8088/out/iptv.m3u`（`{start}/{end}`）
- APTV：`http://<lan-ip>:8088/out/iptv-aptv.m3u`（`${(b)}/${(e)}`）

EPG：`http://<lan-ip>:8088/out/epg.xml`

## 配置

见 [`config.example.yaml`](config.example.yaml)。  
从旧机迁移可参考 [`config.241.example.yaml`](config.241.example.yaml)。

敏感项可用环境变量覆盖：`MQTT_HOST`、`MQTT_PASSWORD`、`CONFIG_PATH`。

## MQTT / Home Assistant

启用 `mqtt.enabled` 并指向 HA 的 MQTT broker 后，自动发布 Discovery，设备名默认 `IPTV Server`。

**状态 topic（retain）：**

- `{prefix}/health` — `online` / `offline`
- `{prefix}/status` — 汇总 JSON
- `{prefix}/m3u`、`{prefix}/epg`、`{prefix}/udpxy`、`{prefix}/job`

**命令 topic：** `{prefix}/cmd`

```json
{"action":"generate"}
```

一键生成会跑 **M3U（含 Logo）+ EPG**。

### Lovelace 卡片

仓库内提供自定义卡片：[`hass/iptv-card/`](hass/iptv-card/README.md)。

```yaml
type: custom:iptv-control-card
title: IPTV 241
prefix: iptv_241
```

## 架构

详见 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)。
