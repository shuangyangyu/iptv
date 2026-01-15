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
from ..utils.state import append_log, load_state, now_ts, save_state
from .state import get_server_base_url

logger = logging.getLogger(__name__)


def build_m3u_args(cfg: Dict[str, Any], web_base_url: str = None, x_tvg_url: str = None, udpxy_base: str = None) -> List[str]:
    """
    构建 build_m3u.py 的命令行参数
    
    UDPXY 始终启用（因为 UDPXY 是程序运行的前提，必须使用）
    udpxy_base 优先使用传入的参数，否则从 local_iface 自动构建
    """
    args = []
    if cfg.get("input_url"):
        args.extend(["--input", str(cfg["input_url"])])
    if cfg.get("output_m3u"):
        # 只使用文件名（去掉路径部分），自动拼接 out/ 目录
        m3u_filename = Path(cfg["output_m3u"]).name
        out_path = OUT_DIR / m3u_filename
        args.extend(["--out", str(out_path)])
    if cfg.get("source_iface"):
        args.extend(["--source-iface", str(cfg["source_iface"])])
    
    # UDPXY 始终启用（不再检查 use_udpxy）
    # 优先使用传入的 udpxy_base（如果提供了）
    if udpxy_base:
        args.extend(["--udpxy", str(udpxy_base)])
    elif cfg.get("udpxy_base"):
        # 如果没有传入，使用配置中的值
        args.extend(["--udpxy", str(cfg["udpxy_base"])])
    else:
        # 最后的回退：尝试从 local_iface 自动构建（如果可能）
        try:
            from .udpxy import get_udpxy_base_url
            auto_udpxy_base = get_udpxy_base_url(cfg)
            args.extend(["--udpxy", auto_udpxy_base])
        except Exception:
            # 如果自动构建失败，使用默认值（但不应该到达这里）
            logger.warning("无法自动构建 udpxy_base，使用默认值")
            args.extend(["--udpxy", "http://192.168.1.250:4022"])
    
    # x_tvg_url 优先使用传入的动态地址
    if x_tvg_url:
        args.extend(["--x-tvg-url", x_tvg_url])
    elif cfg.get("x_tvg_url"):
        # 如果没有传入动态地址，使用配置中的值（向后兼容）
        args.extend(["--x-tvg-url", str(cfg["x_tvg_url"])])
    if cfg.get("timeout_s"):
        args.extend(["--timeout", str(cfg["timeout_s"])])
    if cfg.get("user_agent"):
        args.extend(["--user-agent", str(cfg["user_agent"])])
    if cfg.get("download_logos"):
        args.append("--download-logos")
    if not cfg.get("localize_logos", True):
        args.append("--no-localize-logos")
    # logo_dir 已移除，固定使用 out/logos/（由后端自动推导）
    # web_base_url 从 local_iface 动态获取（传入参数）
    if not web_base_url:
        web_base_url = get_server_base_url(cfg, port=8088)
    args.extend(["--web-base-url", web_base_url])
    # logo_timeout_s 和 logo_delay_s 已移除，使用默认值（10.0 和 0.05）
    if not cfg.get("logo_skip_existing", True):
        args.append("--no-logo-skip-existing")
    return args


def build_epg_args(cfg: Dict[str, Any], web_base_url: str = None) -> List[str]:
    """构建 build_epg.py 的命令行参数"""
    args = []
    if cfg.get("channels_url") or cfg.get("input_url"):
        args.extend(["--channels-url", str(cfg.get("channels_url") or cfg.get("input_url", ""))])
    if cfg.get("epg_out"):
        # 只使用文件名（去掉路径部分），自动拼接 out/ 目录
        epg_filename = Path(cfg["epg_out"]).name
        out_path = OUT_DIR / epg_filename
        args.extend(["--out", str(out_path)])
    if cfg.get("epg_base_url"):
        args.extend(["--base-url", str(cfg["epg_base_url"])])
    if cfg.get("epg_riddle"):
        args.extend(["--riddle", str(cfg["epg_riddle"])])
    if cfg.get("epg_time_ms"):
        args.extend(["--time", str(cfg["epg_time_ms"])])
    # 不再使用额外参数（根据文档，这些参数是弱校验/可选的，删除仍能返回JSON）
    if cfg.get("source_iface"):
        args.extend(["--source-iface", str(cfg["source_iface"])])
    # epg_timeout_s 和 epg_sleep_s 已移除，使用默认值（8.0 和 0.05）
    # web_base_url 从 local_iface 动态获取（传入参数）
    if not web_base_url:
        web_base_url = get_server_base_url(cfg, port=8088)
    args.extend(["--web-base-url", web_base_url])
    # logo_dir 已移除，固定使用 out/logos/（由后端自动推导）
    if cfg.get("epg_days_forward") is not None:
        args.extend(["--days-forward", str(cfg["epg_days_forward"])])
    if cfg.get("epg_days_back") is not None:
        args.extend(["--days-back", str(cfg["epg_days_back"])])
    return args


def execute_job(job_type: str, request_host: str = None) -> Dict[str, Any]:
    """
    执行任务
    
    Args:
        job_type: 任务类型（"m3u" | "epg" | "logos"）
        request_host: 请求主机地址（已弃用，不再使用）
    
    Returns:
        任务执行结果
    """
    from .state import get_server_base_url
    from .udpxy import get_udpxy_base_url
    
    state = load_state()
    job_type = (job_type or "").strip().lower()
    
    if job_type not in {"m3u", "epg", "logos"}:
        from .state import get_status
        full_status = get_status()
        return {
            "ok": False,
            "error": f"unknown job: {job_type}",
            "status": full_status,
            "download_url": None,
        }
    
    cfg = state.get("config", {})
    append_log(state, "INFO", f"开始执行任务：{job_type}")
    
    # 构建 web_base_url（从 local_iface 获取，不再使用 request_host）
    web_base_url = get_server_base_url(cfg, port=8088)
    append_log(state, "INFO", f"使用 web_base_url: {web_base_url} (从 local_iface 获取)")
    
    # UDPXY 始终启用，获取 udpxy_base（从 local_iface 获取）
    udpxy_base = get_udpxy_base_url(cfg)
    # 更新 cfg 中的 udpxy_base，用于传递给 build_m3u_args
    cfg["udpxy_base"] = udpxy_base
    append_log(state, "INFO", f"使用 udpxy_base: {udpxy_base} (从 local_iface 获取，UDPXY 始终启用)")
    
    # 构建脚本路径
    backend_dir = IPTV_SEVER_DIR / "backend"
    
    if job_type == "m3u":
        script_path = backend_dir / "build_m3u.py"
        epg_filename = Path(cfg.get("epg_out", "epg.xml")).name
        x_tvg_url = f"{web_base_url}/out/{epg_filename}"
        args = build_m3u_args(cfg, web_base_url=web_base_url, x_tvg_url=x_tvg_url, udpxy_base=udpxy_base)
    elif job_type == "epg":
        script_path = backend_dir / "build_epg.py"
        args = build_epg_args(cfg, web_base_url=web_base_url)
    else:  # logos
        append_log(state, "WARN", "Logo 下载会在生成 M3U 时自动执行")
        save_state(state)
        from .state import get_status
        full_status = get_status()
        return {
            "ok": True,
            "status": full_status,
            "download_url": None,  # logos 任务没有单独的下载路径
        }
    
    if not script_path.exists():
        append_log(state, "ERROR", f"脚本不存在：{script_path}")
        save_state(state)
        from .state import get_status
        full_status = get_status()
        return {
            "ok": False,
            "error": f"脚本不存在：{script_path}",
            "status": full_status,
            "download_url": None,
        }
    
    # 执行脚本
    try:
        cmd = ["python3", str(script_path)] + args
        append_log(state, "INFO", f"执行命令：{' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
        )
        
        # 更新状态
        st = state.setdefault("status", {})
        st["last_job"] = job_type
        st["last_job_rc"] = result.returncode
        st["last_job_at"] = now_ts()
        
        if result.returncode == 0:
            # 检查输出文件是否存在
            if job_type == "m3u":
                out_path_str = cfg.get("output_m3u", "iptv.m3u")
                m3u_filename = Path(out_path_str).name
                out_path = OUT_DIR / m3u_filename
                if out_path.exists():
                    st["m3u"] = {
                        "exists": True,
                        "size": out_path.stat().st_size,
                        "mtime": int(out_path.stat().st_mtime),
                    }
                append_log(state, "OK", "M3U 生成完成")
                
                # 提取并保存回放服务器地址
                try:
                    from iptv_sever.backend.core import extract_channels, load_channel_categories
                    from iptv_sever.backend.net import build_opener, get_ipv4_from_iface
                    
                    # 重新加载 channel_5.js 提取地址
                    bind_ip = get_ipv4_from_iface(cfg.get("source_iface", "eth1"))
                    if bind_ip:
                        opener = build_opener(bind_ip)
                        categories = load_channel_categories(
                            cfg.get("input_url", ""),
                            opener=opener,
                            timeout_s=cfg.get("timeout_s", 10.0),
                            user_agent=cfg.get("user_agent", "curl/8.0.0"),
                        )
                        # web_base_url 参数传入空字符串，因为我们只需要提取地址，不需要构建 catchup_source
                        _, catchup_host, catchup_port, virtual_domain = extract_channels(
                            categories,
                            tvg_id_field="primaryid",
                            web_base_url=""
                        )
                        
                        # 更新配置（会在函数末尾统一保存）
                        if catchup_host and catchup_port:
                            if "catchup" not in state["config"]:
                                state["config"]["catchup"] = {}
                            state["config"]["catchup"]["target_host"] = catchup_host
                            state["config"]["catchup"]["target_port"] = catchup_port
                            if virtual_domain:
                                state["config"]["catchup"]["virtual_domain"] = virtual_domain
                            append_log(state, "INFO", f"已更新回放服务器配置: {catchup_host}:{catchup_port}")
                        else:
                            append_log(state, "WARN", f"未能从 channel_5.js 提取回放服务器地址（可能 zx 字段为空或格式不正确）")
                    else:
                        append_log(state, "WARN", f"无法获取绑定 IP，跳过回放服务器地址提取")
                except Exception as e:
                    logger.warning(f"提取回放服务器地址失败: {e}", exc_info=True)
                    append_log(state, "ERROR", f"提取回放服务器地址异常: {str(e)}")
                    # 不影响 M3U 生成任务的成功状态
            elif job_type == "epg":
                out_path_str = cfg.get("epg_out", "epg.xml")
                epg_filename = Path(out_path_str).name
                out_path = OUT_DIR / epg_filename
                if out_path.exists():
                    st["epg"] = {
                        "exists": True,
                        "size": out_path.stat().st_size,
                        "mtime": int(out_path.stat().st_mtime),
                    }
                append_log(state, "OK", "EPG 生成完成")
        else:
            append_log(state, "ERROR", f"执行失败（退出码 {result.returncode}）")
            if result.stderr:
                append_log(state, "ERROR", f"错误输出：{result.stderr[:500]}")
        
        if result.stdout:
            append_log(state, "INFO", f"输出：{result.stdout[:500]}")
    
    except subprocess.TimeoutExpired:
        append_log(state, "ERROR", "执行超时（超过 5 分钟）")
        st = state.setdefault("status", {})
        st["last_job"] = job_type
        st["last_job_rc"] = -1
        st["last_job_at"] = now_ts()
    except Exception as e:
        append_log(state, "ERROR", f"执行异常：{str(e)}")
        st = state.setdefault("status", {})
        st["last_job"] = job_type
        st["last_job_rc"] = -1
        st["last_job_at"] = now_ts()
    
    save_state(state)
    
    # 确保返回完整的状态信息（包括 m3u 和 epg 的实时状态）
    from .state import get_status
    full_status = get_status()
    
    # 计算下载路径（如果任务成功且文件存在）
    download_url = None
    if job_type == "m3u" and full_status.get("m3u", {}).get("exists"):
        m3u_filename = Path(cfg.get("output_m3u", "iptv.m3u")).name
        download_url = f"{web_base_url}/out/{m3u_filename}"
    elif job_type == "epg" and full_status.get("epg", {}).get("exists"):
        epg_filename = Path(cfg.get("epg_out", "epg.xml")).name
        download_url = f"{web_base_url}/out/{epg_filename}"
    # logos 任务没有单独的下载路径（logos 在 M3U 生成时自动下载）
    
    return {
        "ok": True,
        "status": full_status,
        "download_url": download_url,
    }

