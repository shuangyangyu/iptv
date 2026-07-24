# IPTV Server

YAML 配置 + udpxy 直播 + 回看反代 + MQTT / Home Assistant。无 Web 管理 UI。

## 文档

- 根目录 [`README.md`](../README.md)：快速开始
- [`TECHNICAL.md`](TECHNICAL.md)：架构与 MQTT
- [`README_DOCKER.md`](README_DOCKER.md)：Docker 细节
- [`README_HA部署.md`](README_HA部署.md)：与 HA 同机/同网部署说明

## 目录

```text
iptv_sever/
├── api/           # FastAPI：health /out /catchup + 调度
├── backend/       # m3u/epg/catchup/udpxy 核心
└── mqtt/          # MQTT 状态、Discovery、命令
config.example.yaml
docker-compose.yml
```
