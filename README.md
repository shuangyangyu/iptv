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
| 8088 | `/out` m3u/epg、`/catchup` 回看、`/health` |
| 4022 | udpxy 直播 |

播放列表：`http://<lan-ip>:8088/out/iptv.m3u`  
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
{"action":"job","name":"m3u"}
{"action":"job","name":"epg"}
{"action":"udpxy","name":"restart"}
```

HA 中会出现 button：Run M3U / Run EPG / Restart UDPXY 等。

## 架构

详见 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)。
