#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务执行 API 路由
"""

from fastapi import APIRouter, Request

from ..models.job import JobResponse
from ..services.job import execute_job

router = APIRouter(prefix="/api/v1", tags=["任务执行"])


@router.post("/jobs/{job_type}", response_model=JobResponse)
async def api_run_job(job_type: str, request: Request):
    """
    执行生成任务
    
    执行 M3U 或 EPG 生成任务，调用后端 Python 脚本并更新系统状态。
    任务执行可能需要较长时间（最多 5 分钟），建议异步调用。
    
    **任务类型说明**：
    - `m3u`: 生成 M3U 播放列表文件，调用 `backend/build_m3u.py`
      - 会根据配置下载频道列表，转换 URL（如果需要），下载 Logo，生成 M3U 文件
      - 如果配置了 `download_logos: true`，会在生成 M3U 时自动下载 Logo
    - `epg`: 生成 EPG 电子节目单文件，调用 `backend/build_epg.py`
      - 会根据配置从 EPG API 获取节目信息，生成 XMLTV 格式的 EPG 文件
    - `logos`: Logo 下载任务（单独调用会返回成功但不执行）
      - Logo 下载会在 `m3u` 任务执行时自动进行，不需要单独调用
      - 如果单独调用 `logos` 任务，会直接返回成功，不会执行实际下载
    
    **请求参数**：
    - `job_type` (路径参数): 任务类型，必须是 `m3u`、`epg` 或 `logos`（不区分大小写）
    - `Host` (HTTP Header): 可选，请求的主机地址，用于构建 `web_base_url`
      - 如果未提供，会从配置中获取或使用默认值
      - 用于生成 M3U 文件中的 EPG URL 和 Logo URL
    
    **响应说明**：
    - `ok`: 请求是否成功（即使任务执行失败，请求本身也可能成功）
    - `status`: 系统状态对象，包含：
      - `last_job`: 最后执行的任务类型（`"m3u"` | `"epg"` | `"logos"` | `null`）
      - `last_job_rc`: 任务退出码（`0`=成功，非`0`=失败，`-1`=超时或异常，`null`=未执行）
      - `last_job_at`: 任务执行时间（Unix 时间戳，秒）
      - `m3u`: M3U 文件状态对象（仅当执行 `m3u` 任务后才有）
        - `exists`: 文件是否存在
        - `size`: 文件大小（字节）
        - `mtime`: 文件修改时间（Unix 时间戳）
      - `epg`: EPG 文件状态对象（仅当执行 `epg` 任务后才有）
        - `exists`: 文件是否存在
        - `size`: 文件大小（字节）
        - `mtime`: 文件修改时间（Unix 时间戳）
      - `udpxy`: UDPXY 服务状态对象（如果有）
    - `download_url`: 生成文件的下载 URL（仅在任务成功且文件存在时返回）
      - M3U 任务：`http://{local_iface_ip}:8088/out/{m3u_filename}`
      - EPG 任务：`http://{local_iface_ip}:8088/out/{epg_filename}`
      - Logos 任务：`null`（logos 在 M3U 生成时自动下载，没有单独下载路径）
      - 如果任务失败或文件不存在，则为 `null`
    - `error`: 错误信息（仅在请求失败时返回，例如无效的 job_type）
    
    **执行超时**：
    - 任务执行超时时间为 5 分钟（300秒）
    - 如果任务执行超时，`last_job_rc` 会被设置为 `-1`
    
    **注意事项**：
    - 任务执行是同步的，可能需要较长时间（特别是 M3U 生成，涉及网络请求和文件下载）
    - 任务执行期间会记录日志，可以通过 `/api/v1/logs` 查看执行日志
    - 任务执行会更新系统状态，执行结果可以通过 `/api/v1/status` 查看
    - `logos` 任务不会实际执行，会在 M3U 生成时自动进行
    - 如果脚本不存在，会返回错误信息
    
    **使用示例**：
    ```bash
    # 执行 M3U 生成任务
    curl -X POST http://localhost:8088/api/v1/jobs/m3u
    
    # 执行 EPG 生成任务
    curl -X POST http://localhost:8088/api/v1/jobs/epg
    
    # 执行 Logo 下载任务（不会实际执行，会直接返回成功）
    curl -X POST http://localhost:8088/api/v1/jobs/logos
    ```
    
    **成功响应示例**（M3U 任务）：
    ```json
    {
      "ok": true,
      "status": {
        "m3u": {
          "exists": true,
          "size": 123456,
          "mtime": 1766466475
        },
        "last_job": "m3u",
        "last_job_rc": 0,
        "last_job_at": 1766466475
      },
      "download_url": "http://192.168.1.241:8088/out/iptv.m3u",
      "error": null
    }
    ```
    
    **错误响应**：
    - 如果 `job_type` 无效，返回 200 状态码，但 `ok` 为 `false`：
    ```json
    {
      "ok": false,
      "error": "unknown job: invalid_type",
      "status": { ... },
      "download_url": null
    }
    ```
    - 如果脚本不存在，返回 200 状态码，但 `ok` 为 `false`：
    ```json
    {
      "ok": false,
      "error": "脚本不存在：/path/to/script.py",
      "status": { ... },
      "download_url": null
    }
    ```
    """
    # 从请求中获取主机地址
    request_host = request.headers.get("host", None)
    result = execute_job(job_type, request_host)
    return result

