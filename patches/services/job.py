#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务执行服务
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from ..config import IPTV_SEVER_DIR, OUT_DIR
from ..runtime_status import (
    append_runtime_log,
    now_ts,
    update_file_status,
    update_job_result,
)
from .state import get_config, get_server_base_url, get_status, publish_status_mqtt

logger = logging.getLogger(__name__)


def build_m3u_args(
    cfg: Dict[str, Any],
    web_base_url: str = None,
    x_tvg_url: str = None,
    udpxy_base: str = None,
) -> List[str]:
    args = []
    if cfg.get("input_url"):
        args.extend(["--input", str(cfg["input_url"])])
    if cfg.get("output_m3u"):
        m3u_filename = Path(cfg["output_m3u"]).name
        out_path = OUT_DIR / m3u_filename
        args.extend(["--out", str(out_path)])
    if cfg.get("source_iface"):
        args.extend(["--source-iface", str(cfg["source_iface"])])

    if udpxy_base:
        args.extend(["--udpxy", str(udpxy_base)])
    elif cfg.get("udpxy_base"):
        args.extend(["--udpxy", str(cfg["udpxy_base"])])
    else:
        try:
            from .udpxy import get_udpxy_base_url

            args.extend(["--udpxy", get_udpxy_base_url(cfg)])
        except Exception:
            args.extend(["--udpxy", "http://192.168.1.250:4022"])

    if x_tvg_url:
        args.extend(["--x-tvg-url", x_tvg_url])
    elif cfg.get("x_tvg_url"):
        args.extend(["--x-tvg-url", str(cfg["x_tvg_url"])])
    if cfg.get("timeout_s"):
        args.extend(["--timeout", str(cfg["timeout_s"])])
    if cfg.get("user_agent"):
        args.extend(["--user-agent", str(cfg["user_agent"])])
    if cfg.get("download_logos"):
        args.append("--download-logos")
    if not cfg.get("localize_logos", True):
        args.append("--no-localize-logos")
    if not web_base_url:
        web_base_url = get_server_base_url(cfg, port=int(cfg.get("http_port") or 8088))
    args.extend(["--web-base-url", web_base_url])
    if not cfg.get("logo_skip_existing", True):
        args.append("--no-logo-skip-existing")
    return args


def build_epg_args(cfg: Dict[str, Any], web_base_url: str = None) -> List[str]:
    args = []
    if cfg.get("channels_url") or cfg.get("input_url"):
        args.extend(
            [
                "--channels-url",
                str(cfg.get("channels_url") or cfg.get("input_url", "")),
            ]
        )
    if cfg.get("epg_out"):
        epg_filename = Path(cfg["epg_out"]).name
        out_path = OUT_DIR / epg_filename
        args.extend(["--out", str(out_path)])
    if cfg.get("epg_base_url"):
        args.extend(["--base-url", str(cfg["epg_base_url"])])
    if cfg.get("epg_riddle"):
        args.extend(["--riddle", str(cfg["epg_riddle"])])
    if cfg.get("epg_time_ms"):
        args.extend(["--time", str(cfg["epg_time_ms"])])
    if cfg.get("source_iface"):
        args.extend(["--source-iface", str(cfg["source_iface"])])
    if not web_base_url:
        web_base_url = get_server_base_url(cfg, port=int(cfg.get("http_port") or 8088))
    args.extend(["--web-base-url", web_base_url])
    if cfg.get("epg_days_forward") is not None:
        args.extend(["--days-forward", str(cfg["epg_days_forward"])])
    if cfg.get("epg_days_back") is not None:
        args.extend(["--days-back", str(cfg["epg_days_back"])])
    return args


def execute_job(job_type: str, request_host: str = None) -> Dict[str, Any]:
    from .udpxy import get_udpxy_base_url
    from .state import set_catchup_override

    job_type = (job_type or "").strip().lower()
    if job_type not in {"m3u", "epg", "logos"}:
        return {
            "ok": False,
            "error": f"unknown job: {job_type}",
            "status": get_status(),
            "download_url": None,
        }

    cfg = get_config()
    append_runtime_log("INFO", f"开始执行任务：{job_type}")

    port = int(cfg.get("http_port") or 8088)
    web_base_url = get_server_base_url(cfg, port=port)
    udpxy_base = get_udpxy_base_url(cfg)
    cfg["udpxy_base"] = udpxy_base

    backend_dir = IPTV_SEVER_DIR / "backend"

    if job_type == "logos":
        append_runtime_log("WARN", "Logo 下载会在生成 M3U 时自动执行")
        update_job_result("logos", 0)
        publish_status_mqtt()
        return {"ok": True, "status": get_status(), "download_url": None}

    if job_type == "m3u":
        script_path = backend_dir / "build_m3u.py"
        epg_filename = Path(cfg.get("epg_out", "epg.xml")).name
        x_tvg_url = f"{web_base_url}/out/{epg_filename}"
        args = build_m3u_args(
            cfg,
            web_base_url=web_base_url,
            x_tvg_url=x_tvg_url,
            udpxy_base=udpxy_base,
        )
    else:
        script_path = backend_dir / "build_epg.py"
        args = build_epg_args(cfg, web_base_url=web_base_url)

    if not script_path.exists():
        append_runtime_log("ERROR", f"脚本不存在：{script_path}")
        update_job_result(job_type, -1)
        publish_status_mqtt()
        return {
            "ok": False,
            "error": f"脚本不存在：{script_path}",
            "status": get_status(),
            "download_url": None,
        }

    rc = -1
    try:
        cmd = ["python3", str(script_path)] + args
        append_runtime_log("INFO", f"执行命令：{' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )
        rc = result.returncode
        update_job_result(job_type, rc)

        if rc == 0:
            if job_type == "m3u":
                m3u_filename = Path(cfg.get("output_m3u", "iptv.m3u")).name
                out_path = OUT_DIR / m3u_filename
                if out_path.exists():
                    update_file_status(
                        "m3u",
                        {
                            "exists": True,
                            "size": out_path.stat().st_size,
                            "mtime": int(out_path.stat().st_mtime),
                        },
                    )
                append_runtime_log("OK", "M3U 生成完成")
                try:
                    from iptv_sever.backend.core import (
                        extract_channels,
                        load_channel_categories,
                    )
                    from iptv_sever.backend.net import (
                        build_opener,
                        get_ipv4_from_iface,
                    )

                    bind_ip = get_ipv4_from_iface(cfg.get("source_iface", "eth1"))
                    if bind_ip:
                        opener = build_opener(bind_ip)
                        categories = load_channel_categories(
                            cfg.get("input_url", ""),
                            opener=opener,
                            timeout_s=cfg.get("timeout_s", 10.0),
                            user_agent=cfg.get("user_agent", "curl/8.0.0"),
                        )
                        _, catchup_host, catchup_port, virtual_domain = extract_channels(
                            categories,
                            tvg_id_field="primaryid",
                            web_base_url="",
                        )
                        if catchup_host and catchup_port:
                            set_catchup_override(
                                target_host=catchup_host,
                                target_port=catchup_port,
                                virtual_domain=virtual_domain,
                            )
                            append_runtime_log(
                                "INFO",
                                f"内存已更新回放地址: {catchup_host}:{catchup_port}",
                            )
                except Exception as e:
                    logger.warning(f"提取回放服务器地址失败: {e}", exc_info=True)
            elif job_type == "epg":
                epg_filename = Path(cfg.get("epg_out", "epg.xml")).name
                out_path = OUT_DIR / epg_filename
                if out_path.exists():
                    update_file_status(
                        "epg",
                        {
                            "exists": True,
                            "size": out_path.stat().st_size,
                            "mtime": int(out_path.stat().st_mtime),
                        },
                    )
                append_runtime_log("OK", "EPG 生成完成")
        else:
            append_runtime_log("ERROR", f"执行失败（退出码 {rc}）")
            if result.stderr:
                append_runtime_log("ERROR", f"错误输出：{result.stderr[:500]}")
        if result.stdout:
            append_runtime_log("INFO", f"输出：{result.stdout[:500]}")
    except subprocess.TimeoutExpired:
        append_runtime_log("ERROR", "执行超时（超过 5 分钟）")
        update_job_result(job_type, -1)
    except Exception as e:
        append_runtime_log("ERROR", f"执行异常：{str(e)}")
        update_job_result(job_type, -1)

    publish_status_mqtt()
    full_status = get_status()
    download_url = None
    if job_type == "m3u" and full_status.get("m3u", {}).get("exists"):
        download_url = f"{web_base_url}/out/{Path(cfg.get('output_m3u', 'iptv.m3u')).name}"
    elif job_type == "epg" and full_status.get("epg", {}).get("exists"):
        download_url = f"{web_base_url}/out/{Path(cfg.get('epg_out', 'epg.xml')).name}"

    return {"ok": rc == 0, "status": full_status, "download_url": download_url}
