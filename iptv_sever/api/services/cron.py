#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cron 服务
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import IPTV_SEVER_DIR
from ..utils.state import append_log, load_state, save_state


def get_cron_status() -> Dict[str, Any]:
    """
    获取 Cron 任务状态
    """
    backend_dir = IPTV_SEVER_DIR / "backend"
    build_epg_script = backend_dir / "build_epg.py"
    
    is_enabled = False
    cron_expr = None
    cron_cmd = None
    next_run_info = None
    
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0:
            crontab_content = result.stdout
            for line in crontab_content.split("\n"):
                if str(build_epg_script) in line and not line.strip().startswith("#"):
                    is_enabled = True
                    parts = line.strip().split(None, 5)
                    if len(parts) >= 6:
                        cron_expr = " ".join(parts[:5])
                        cron_cmd = parts[5]
                    break
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    except Exception:
        pass
    
    if cron_expr:
        try:
            next_run_info = f"Cron表达式: {cron_expr}"
        except Exception:
            pass
    
    return {
        "enabled": is_enabled,
        "cron_expr": cron_expr,
        "cron_cmd": cron_cmd,
        "next_run_info": next_run_info,
    }


def setup_cron(
    mode: str,
    interval_hours: Optional[int] = None,
    interval_minutes: Optional[int] = None,
    cron_hour: Optional[str] = None,
    cron_minute: Optional[str] = None,
    source_iface: Optional[str] = None,
) -> Dict[str, Any]:
    """
    设置 Cron 任务
    """
    backend_dir = IPTV_SEVER_DIR / "backend"
    setup_script = backend_dir / "setup_cron.sh"
    
    if not setup_script.exists():
        return {
            "ok": False,
            "error": "Cron设置脚本不存在",
        }
    
    state = load_state()
    cfg = state.get("config", {})
    source_iface = source_iface or cfg.get("source_iface", "eth1")
    
    cmd = ["bash", str(setup_script)]
    if mode == "interval":
        cmd.extend([
            "--interval-hours", str(interval_hours),
            "--source-iface", str(source_iface),
        ])
        if interval_minutes and interval_minutes > 0:
            cmd.extend(["--interval-minutes", str(interval_minutes)])
    else:  # cron
        cmd.extend([
            "--cron-hour", str(cron_hour),
            "--cron-minute", str(cron_minute),
            "--source-iface", str(source_iface),
        ])
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode == 0:
            mode_desc = f"间隔模式（每{interval_hours}小时）" if mode == "interval" else f"Cron模式（{cron_hour}:{cron_minute}）"
            append_log(state, "INFO", f"Cron任务已设置：{mode_desc}")
            save_state(state)
            return {
                "ok": True,
                "message": "Cron任务已设置",
                "output": result.stdout,
            }
        else:
            error_msg = result.stderr or result.stdout or "设置失败"
            append_log(state, "ERROR", f"设置Cron任务失败: {error_msg}")
            save_state(state)
            return {
                "ok": False,
                "error": error_msg,
            }
    except Exception as e:
        state = load_state()
        append_log(state, "ERROR", f"设置Cron任务异常: {str(e)}")
        save_state(state)
        return {
            "ok": False,
            "error": str(e),
        }


def remove_cron() -> Dict[str, Any]:
    """
    移除 Cron 任务
    """
    backend_dir = IPTV_SEVER_DIR / "backend"
    setup_script = backend_dir / "setup_cron.sh"
    
    if not setup_script.exists():
        return {
            "ok": False,
            "error": "Cron设置脚本不存在",
        }
    
    try:
        result = subprocess.run(
            ["bash", str(setup_script), "--remove"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        state = load_state()
        if result.returncode == 0:
            append_log(state, "INFO", "Cron任务已移除")
            save_state(state)
            return {
                "ok": True,
                "message": "Cron任务已移除",
                "output": result.stdout,
            }
        else:
            error_msg = result.stderr or result.stdout or "移除失败"
            append_log(state, "ERROR", f"移除Cron任务失败: {error_msg}")
            save_state(state)
            return {
                "ok": False,
                "error": error_msg,
            }
    except Exception as e:
        state = load_state()
        append_log(state, "ERROR", f"移除Cron任务异常: {str(e)}")
        save_state(state)
        return {
            "ok": False,
            "error": str(e),
        }

