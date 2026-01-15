#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
环境检测服务
"""

import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import urllib.request

from ..config import IPTV_SEVER_DIR, LOG_FILE, OUT_DIR
from ..utils.network import (
    get_all_interfaces,
    get_interface_detail,
    get_interface_ip,
    run_test_script,
)
from ..utils.state import append_log, load_state, save_state, now_ts
from .state import get_config
from .udpxy import get_udpxy_config, get_udpxy_status


def check_environment() -> Dict[str, Any]:
    """
    执行完整的系统环境检测
    
    Returns:
        包含所有检测结果的字典，格式符合 EnvironmentCheckResponse 模型
    """
    state = load_state()
    cfg = get_config()
    
    # 记录检测开始
    append_log(state, "INFO", "环境检测开始")
    save_state(state)
    
    # 初始化检测结果容器
    all_items: List[Dict[str, Any]] = []
    categories: Dict[str, Dict[str, Any]] = {
        "network": {"items": [], "passed": 0, "failed": 0, "warnings": 0},
        "udpxy": {"items": [], "passed": 0, "failed": 0, "warnings": 0},
        "files": {"items": [], "passed": 0, "failed": 0, "warnings": 0},
        "config": {"items": [], "passed": 0, "failed": 0, "warnings": 0},
        "services": {"items": [], "passed": 0, "failed": 0, "warnings": 0},
    }
    
    # 执行各项检测
    _check_network(cfg, categories["network"]["items"], state)
    _check_udpxy(cfg, categories["udpxy"]["items"], state)
    _check_files(cfg, categories["files"]["items"], state)
    _check_config(cfg, categories["config"]["items"], state)
    _check_services(cfg, categories["services"]["items"], state)
    
    # 汇总统计
    total_passed = 0
    total_failed = 0
    total_warnings = 0
    
    for category_name, category_data in categories.items():
        for item in category_data["items"]:
            if item["status"] == "ok":
                category_data["passed"] += 1
                total_passed += 1
            elif item["status"] == "error":
                category_data["failed"] += 1
                total_failed += 1
            elif item["status"] == "warn":
                category_data["warnings"] += 1
                total_warnings += 1
            all_items.append(item)
        
        # 判断分类是否全部通过
        category_data["ok"] = category_data["failed"] == 0
        category_data["category"] = category_name
    
    # 提取所有不合格项
    failed_items = [item for item in all_items if item["status"] in ("error", "warn")]
    
    # 整体是否达标（只要有一个 error 就不达标）
    overall_ok = total_failed == 0
    
    # 记录检测完成
    summary_msg = f"环境检测完成: 通过 {total_passed} 项, 失败 {total_failed} 项, 警告 {total_warnings} 项"
    append_log(state, "INFO", summary_msg)
    save_state(state)
    
    return {
        "ok": overall_ok,
        "timestamp": now_ts(),
        "summary": {
            "total": total_passed + total_failed + total_warnings,
            "passed": total_passed,
            "failed": total_failed,
            "warnings": total_warnings,
        },
        "categories": categories,
        "failed_items": failed_items,
    }


def _check_network(cfg: Dict[str, Any], items: List[Dict[str, Any]], state: Dict[str, Any]) -> None:
    """网络配置检测"""
    # 获取所有接口
    all_interfaces = get_all_interfaces()
    interface_names = [iface["name"] for iface in all_interfaces]
    
    # 检查 source_iface
    source_iface = cfg.get("source_iface", "eth1")
    try:
        iface_detail = get_interface_detail(source_iface)
        if source_iface not in interface_names:
            items.append({
                "category": "network",
                "name": f"源网络接口 {source_iface} 存在性",
                "status": "error",
                "message": f"网络接口 {source_iface} 不存在",
            })
            append_log(state, "ERROR", f"检测项: 源网络接口 {source_iface} 存在性 - 网络接口 {source_iface} 不存在")
        elif not iface_detail.get("has_ip"):
            items.append({
                "category": "network",
                "name": f"源网络接口 {source_iface} IP 配置",
                "status": "warn",
                "message": f"网络接口 {source_iface} 未配置 IP 地址",
            })
            append_log(state, "WARN", f"检测项: 源网络接口 {source_iface} IP 配置 - 网络接口 {source_iface} 未配置 IP 地址")
        else:
            ip = iface_detail.get("ip")
            items.append({
                "category": "network",
                "name": f"源网络接口 {source_iface} IP 配置",
                "status": "ok",
                "message": f"网络接口 {source_iface} 已配置 IP: {ip}",
                "details": {"ip": ip},
            })
            append_log(state, "OK", f"检测项: 源网络接口 {source_iface} IP 配置 - 网络接口 {source_iface} 已配置 IP: {ip}")
    except Exception as e:
        items.append({
            "category": "network",
            "name": f"源网络接口 {source_iface} 检测",
            "status": "error",
            "message": f"检测失败: {str(e)}",
        })
        append_log(state, "ERROR", f"检测项: 源网络接口 {source_iface} 检测 - 检测失败: {str(e)}")
    
    # 检查 local_iface
    local_iface = cfg.get("local_iface")
    if local_iface:
        try:
            iface_detail = get_interface_detail(local_iface)
            if local_iface not in interface_names:
                items.append({
                    "category": "network",
                    "name": f"本地网络接口 {local_iface} 存在性",
                    "status": "error",
                    "message": f"网络接口 {local_iface} 不存在",
                })
                append_log(state, "ERROR", f"检测项: 本地网络接口 {local_iface} 存在性 - 网络接口 {local_iface} 不存在")
            elif not iface_detail.get("has_ip"):
                items.append({
                    "category": "network",
                    "name": f"本地网络接口 {local_iface} IP 配置",
                    "status": "warn",
                    "message": f"网络接口 {local_iface} 未配置 IP 地址",
                })
                append_log(state, "WARN", f"检测项: 本地网络接口 {local_iface} IP 配置 - 网络接口 {local_iface} 未配置 IP 地址")
            else:
                ip = iface_detail.get("ip")
                items.append({
                    "category": "network",
                    "name": f"本地网络接口 {local_iface} IP 配置",
                    "status": "ok",
                    "message": f"网络接口 {local_iface} 已配置 IP: {ip}",
                    "details": {"ip": ip},
                })
                append_log(state, "OK", f"检测项: 本地网络接口 {local_iface} IP 配置 - 网络接口 {local_iface} 已配置 IP: {ip}")
        except Exception as e:
            items.append({
                "category": "network",
                "name": f"本地网络接口 {local_iface} 检测",
                "status": "error",
                "message": f"检测失败: {str(e)}",
            })
            append_log(state, "ERROR", f"检测项: 本地网络接口 {local_iface} 检测 - 检测失败: {str(e)}")
    
    # 测试 M3U 源地址连通性
    input_url = cfg.get("input_url")
    if input_url:
        try:
            if IPTV_SEVER_DIR:
                backend_dir = IPTV_SEVER_DIR / "backend"
                test_script = backend_dir / "check_interfaces.py"
                if test_script.exists():
                    timeout_s = float(cfg.get("timeout_s", 10.0))
                    args = [
                        input_url,
                        "",  # epg_url (空)
                        source_iface or "eth1",
                        str(timeout_s),
                    ]
                    success, result, error_msg = run_test_script(test_script, args, timeout_s, "m3u")
                    m3u_status = result.get("m3u", {}).get("status", "")
                    if success and m3u_status == "success":
                        items.append({
                            "category": "network",
                            "name": "M3U 源地址连通性",
                            "status": "ok",
                            "message": f"M3U 源地址可访问: {input_url}",
                            "details": {"url": input_url},
                        })
                        append_log(state, "OK", f"检测项: M3U 源地址连通性 - M3U 源地址可访问: {input_url}")
                    else:
                        error_detail = result.get("m3u", {}).get("message", error_msg or "连接失败")
                        items.append({
                            "category": "network",
                            "name": "M3U 源地址连通性",
                            "status": "error",
                            "message": f"M3U 源地址无法访问: {input_url} ({error_detail})",
                            "details": {"url": input_url, "error": error_detail},
                        })
                        append_log(state, "ERROR", f"检测项: M3U 源地址连通性 - M3U 源地址无法访问: {input_url} ({error_detail})")
                else:
                    items.append({
                        "category": "network",
                        "name": "M3U 源地址连通性",
                        "status": "warn",
                        "message": "测试脚本不存在，无法检测",
                    })
                    append_log(state, "WARN", "检测项: M3U 源地址连通性 - 测试脚本不存在，无法检测")
        except Exception as e:
            items.append({
                "category": "network",
                "name": "M3U 源地址连通性",
                "status": "error",
                "message": f"检测失败: {str(e)}",
            })
            append_log(state, "ERROR", f"检测项: M3U 源地址连通性 - 检测失败: {str(e)}")
    else:
        items.append({
            "category": "network",
            "name": "M3U 源地址配置",
            "status": "warn",
            "message": "未配置 M3U 源地址",
        })
        append_log(state, "WARN", "检测项: M3U 源地址配置 - 未配置 M3U 源地址")
    
    # 测试 EPG 源地址连通性
    epg_base_url = cfg.get("epg_base_url")
    if epg_base_url:
        try:
            if IPTV_SEVER_DIR:
                backend_dir = IPTV_SEVER_DIR / "backend"
                test_script = backend_dir / "check_interfaces.py"
                if test_script.exists():
                    timeout_s = float(cfg.get("timeout_s", 10.0))
                    args = [
                        "",  # m3u_url (空)
                        epg_base_url,
                        source_iface or "eth1",
                        str(timeout_s),
                    ]
                    success, result, error_msg = run_test_script(test_script, args, timeout_s, "epg")
                    epg_status = result.get("epg", {}).get("status", "")
                    if success and epg_status == "success":
                        items.append({
                            "category": "network",
                            "name": "EPG 源地址连通性",
                            "status": "ok",
                            "message": f"EPG 源地址可访问: {epg_base_url}",
                            "details": {"url": epg_base_url},
                        })
                        append_log(state, "OK", f"检测项: EPG 源地址连通性 - EPG 源地址可访问: {epg_base_url}")
                    else:
                        error_detail = result.get("epg", {}).get("message", error_msg or "连接失败")
                        items.append({
                            "category": "network",
                            "name": "EPG 源地址连通性",
                            "status": "error",
                            "message": f"EPG 源地址无法访问: {epg_base_url} ({error_detail})",
                            "details": {"url": epg_base_url, "error": error_detail},
                        })
                        append_log(state, "ERROR", f"检测项: EPG 源地址连通性 - EPG 源地址无法访问: {epg_base_url} ({error_detail})")
                else:
                    items.append({
                        "category": "network",
                        "name": "EPG 源地址连通性",
                        "status": "warn",
                        "message": "测试脚本不存在，无法检测",
                    })
                    append_log(state, "WARN", "检测项: EPG 源地址连通性 - 测试脚本不存在，无法检测")
        except Exception as e:
            items.append({
                "category": "network",
                "name": "EPG 源地址连通性",
                "status": "error",
                "message": f"检测失败: {str(e)}",
            })
            append_log(state, "ERROR", f"检测项: EPG 源地址连通性 - 检测失败: {str(e)}")
    else:
        items.append({
            "category": "network",
            "name": "EPG 源地址配置",
            "status": "warn",
            "message": "未配置 EPG 源地址",
        })
        append_log(state, "WARN", "检测项: EPG 源地址配置 - 未配置 EPG 源地址")


def _check_udpxy(cfg: Dict[str, Any], items: List[Dict[str, Any]], state: Dict[str, Any]) -> None:
    """UDPXY 服务检测"""
    try:
        import sys
        if IPTV_SEVER_DIR and str(IPTV_SEVER_DIR) not in sys.path:
            sys.path.insert(0, str(IPTV_SEVER_DIR))
        from backend.udpxy_manager import UdpxyManager
        
        udpxy_config = get_udpxy_config()
        manager = UdpxyManager(udpxy_config)
        
        # 检查 UDPXY 程序是否安装
        available, msg = manager.check_available()
        if available:
            items.append({
                "category": "udpxy",
                "name": "UDPXY 程序安装",
                "status": "ok",
                "message": "UDPXY 程序已安装",
            })
            append_log(state, "OK", "检测项: UDPXY 程序安装 - UDPXY 程序已安装")
        else:
            items.append({
                "category": "udpxy",
                "name": "UDPXY 程序安装",
                "status": "error",
                "message": msg,
            })
            append_log(state, "ERROR", f"检测项: UDPXY 程序安装 - {msg}")
            return  # 如果程序未安装，后续检测无法进行
        
        # 检查 UDPXY 服务运行状态
        udpxy_status = get_udpxy_status()
        if udpxy_status.get("running"):
            pid = udpxy_status.get("pid")
            items.append({
                "category": "udpxy",
                "name": "UDPXY 服务运行状态",
                "status": "ok",
                "message": f"UDPXY 服务运行中 (PID: {pid})",
                "details": {"pid": pid},
            })
            append_log(state, "OK", f"检测项: UDPXY 服务运行状态 - UDPXY 服务运行中 (PID: {pid})")
        else:
            items.append({
                "category": "udpxy",
                "name": "UDPXY 服务运行状态",
                "status": "error",
                "message": "UDPXY 服务未运行",
            })
            append_log(state, "ERROR", "检测项: UDPXY 服务运行状态 - UDPXY 服务未运行")
        
        # 检查端口监听状态
        port = udpxy_config.get("port", 4022)
        bind_address = udpxy_config.get("bind_address", "0.0.0.0")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((bind_address if bind_address != "0.0.0.0" else "127.0.0.1", port))
            sock.close()
            if result == 0:
                items.append({
                    "category": "udpxy",
                    "name": "UDPXY 端口监听状态",
                    "status": "ok",
                    "message": f"端口 {port} 正在监听",
                    "details": {"port": port, "bind_address": bind_address},
                })
                append_log(state, "OK", f"检测项: UDPXY 端口监听状态 - 端口 {port} 正在监听")
            else:
                items.append({
                    "category": "udpxy",
                    "name": "UDPXY 端口监听状态",
                    "status": "error",
                    "message": f"端口 {port} 未监听",
                    "details": {"port": port},
                })
                append_log(state, "ERROR", f"检测项: UDPXY 端口监听状态 - 端口 {port} 未监听")
        except Exception as e:
            items.append({
                "category": "udpxy",
                "name": "UDPXY 端口监听状态",
                "status": "warn",
                "message": f"检测失败: {str(e)}",
            })
            append_log(state, "WARN", f"检测项: UDPXY 端口监听状态 - 检测失败: {str(e)}")
        
        # 检查 UDPXY 状态接口可访问性
        if udpxy_status.get("running"):
            udpxy_base = cfg.get("udpxy_base", f"http://192.168.1.250:{port}")
            status_url = f"{udpxy_base}/status"
            try:
                req = urllib.request.Request(status_url)
                req.add_header("User-Agent", "IPTV-Server/1.0")
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        items.append({
                            "category": "udpxy",
                            "name": "UDPXY 状态接口可访问性",
                            "status": "ok",
                            "message": f"状态接口可访问: {status_url}",
                            "details": {"url": status_url},
                        })
                        append_log(state, "OK", f"检测项: UDPXY 状态接口可访问性 - 状态接口可访问: {status_url}")
                    else:
                        items.append({
                            "category": "udpxy",
                            "name": "UDPXY 状态接口可访问性",
                            "status": "warn",
                            "message": f"状态接口返回非 200 状态码: {response.status}",
                            "details": {"url": status_url, "status_code": response.status},
                        })
                        append_log(state, "WARN", f"检测项: UDPXY 状态接口可访问性 - 状态接口返回非 200 状态码: {response.status}")
            except Exception as e:
                items.append({
                    "category": "udpxy",
                    "name": "UDPXY 状态接口可访问性",
                    "status": "warn",
                    "message": f"状态接口无法访问: {str(e)}",
                    "details": {"url": status_url},
                })
                append_log(state, "WARN", f"检测项: UDPXY 状态接口可访问性 - 状态接口无法访问: {str(e)}")
    except Exception as e:
        items.append({
            "category": "udpxy",
            "name": "UDPXY 检测",
            "status": "error",
            "message": f"检测失败: {str(e)}",
        })
        append_log(state, "ERROR", f"检测项: UDPXY 检测 - 检测失败: {str(e)}")


def _check_files(cfg: Dict[str, Any], items: List[Dict[str, Any]], state: Dict[str, Any]) -> None:
    """文件系统检测"""
    # 检查输出目录
    if OUT_DIR.exists():
        try:
            # 尝试创建测试文件检查可写性
            test_file = OUT_DIR / ".write_test"
            test_file.touch()
            test_file.unlink()
            items.append({
                "category": "files",
                "name": "输出目录可写性",
                "status": "ok",
                "message": f"输出目录可写: {OUT_DIR}",
            })
            append_log(state, "OK", f"检测项: 输出目录可写性 - 输出目录可写: {OUT_DIR}")
        except Exception as e:
            items.append({
                "category": "files",
                "name": "输出目录可写性",
                "status": "error",
                "message": f"输出目录不可写: {str(e)}",
            })
            append_log(state, "ERROR", f"检测项: 输出目录可写性 - 输出目录不可写: {str(e)}")
    else:
        try:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            items.append({
                "category": "files",
                "name": "输出目录存在性",
                "status": "ok",
                "message": f"输出目录已创建: {OUT_DIR}",
            })
            append_log(state, "OK", f"检测项: 输出目录存在性 - 输出目录已创建: {OUT_DIR}")
        except Exception as e:
            items.append({
                "category": "files",
                "name": "输出目录存在性",
                "status": "error",
                "message": f"无法创建输出目录: {str(e)}",
            })
            append_log(state, "ERROR", f"检测项: 输出目录存在性 - 无法创建输出目录: {str(e)}")
    
    # 检查 M3U 文件
    m3u_path_str = cfg.get("output_m3u", "iptv.m3u")
    m3u_filename = Path(m3u_path_str).name
    m3u_path = OUT_DIR / m3u_filename
    if m3u_path.exists():
        mtime = m3u_path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        size = m3u_path.stat().st_size
        if age_hours > 24:
            items.append({
                "category": "files",
                "name": "M3U 文件时效性",
                "status": "warn",
                "message": f"M3U 文件已过期: 超过 24 小时未更新 ({age_hours:.1f} 小时)",
                "details": {"age_hours": age_hours, "size": size},
            })
            append_log(state, "WARN", f"检测项: M3U 文件时效性 - M3U 文件已过期: 超过 24 小时未更新 ({age_hours:.1f} 小时)")
        else:
            items.append({
                "category": "files",
                "name": "M3U 文件存在性",
                "status": "ok",
                "message": f"M3U 文件存在 (大小: {size} 字节, 年龄: {age_hours:.1f} 小时)",
                "details": {"size": size, "age_hours": age_hours},
            })
            append_log(state, "OK", f"检测项: M3U 文件存在性 - M3U 文件存在 (大小: {size} 字节, 年龄: {age_hours:.1f} 小时)")
    else:
        items.append({
            "category": "files",
            "name": "M3U 文件存在性",
            "status": "warn",
            "message": "M3U 文件不存在",
        })
        append_log(state, "WARN", "检测项: M3U 文件存在性 - M3U 文件不存在")
    
    # 检查 EPG 文件
    epg_path_str = cfg.get("epg_out", "epg.xml")
    epg_filename = Path(epg_path_str).name
    epg_path = OUT_DIR / epg_filename
    if epg_path.exists():
        mtime = epg_path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        size = epg_path.stat().st_size
        if age_hours > 24:
            items.append({
                "category": "files",
                "name": "EPG 文件时效性",
                "status": "warn",
                "message": f"EPG 文件已过期: 超过 24 小时未更新 ({age_hours:.1f} 小时)",
                "details": {"age_hours": age_hours, "size": size},
            })
            append_log(state, "WARN", f"检测项: EPG 文件时效性 - EPG 文件已过期: 超过 24 小时未更新 ({age_hours:.1f} 小时)")
        else:
            items.append({
                "category": "files",
                "name": "EPG 文件存在性",
                "status": "ok",
                "message": f"EPG 文件存在 (大小: {size} 字节, 年龄: {age_hours:.1f} 小时)",
                "details": {"size": size, "age_hours": age_hours},
            })
            append_log(state, "OK", f"检测项: EPG 文件存在性 - EPG 文件存在 (大小: {size} 字节, 年龄: {age_hours:.1f} 小时)")
    else:
        items.append({
            "category": "files",
            "name": "EPG 文件存在性",
            "status": "warn",
            "message": "EPG 文件不存在",
        })
        append_log(state, "WARN", "检测项: EPG 文件存在性 - EPG 文件不存在")
    
    # 检查日志文件可写性
    if LOG_FILE.parent.exists():
        try:
            # 尝试追加写入
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("")
            items.append({
                "category": "files",
                "name": "日志文件可写性",
                "status": "ok",
                "message": f"日志文件可写: {LOG_FILE}",
            })
            append_log(state, "OK", f"检测项: 日志文件可写性 - 日志文件可写: {LOG_FILE}")
        except Exception as e:
            items.append({
                "category": "files",
                "name": "日志文件可写性",
                "status": "warn",
                "message": f"日志文件不可写: {str(e)}",
            })
            append_log(state, "WARN", f"检测项: 日志文件可写性 - 日志文件不可写: {str(e)}")
    else:
        items.append({
            "category": "files",
            "name": "日志文件目录",
            "status": "warn",
            "message": f"日志文件目录不存在: {LOG_FILE.parent}",
        })
        append_log(state, "WARN", f"检测项: 日志文件目录 - 日志文件目录不存在: {LOG_FILE.parent}")


def _check_config(cfg: Dict[str, Any], items: List[Dict[str, Any]], state: Dict[str, Any]) -> None:
    """配置完整性检测"""
    # 检查必要配置项
    required_fields = {
        "source_iface": "源网络接口",
        "input_url": "M3U 源地址",
    }
    
    for field, field_name in required_fields.items():
        if not cfg.get(field):
            items.append({
                "category": "config",
                "name": f"必要配置项 {field_name}",
                "status": "error",
                "message": f"未配置 {field_name}",
            })
            append_log(state, "ERROR", f"检测项: 必要配置项 {field_name} - 未配置 {field_name}")
        else:
            items.append({
                "category": "config",
                "name": f"必要配置项 {field_name}",
                "status": "ok",
                "message": f"{field_name} 已配置",
            })
            append_log(state, "OK", f"检测项: 必要配置项 {field_name} - {field_name} 已配置")
    
    # 检查配置一致性：source_iface 是否存在
    source_iface = cfg.get("source_iface")
    if source_iface:
        all_interfaces = get_all_interfaces()
        interface_names = [iface["name"] for iface in all_interfaces]
        if source_iface not in interface_names:
            items.append({
                "category": "config",
                "name": "配置一致性：source_iface",
                "status": "error",
                "message": f"配置的 source_iface ({source_iface}) 不存在",
            })
            append_log(state, "ERROR", f"检测项: 配置一致性：source_iface - 配置的 source_iface ({source_iface}) 不存在")
        else:
            items.append({
                "category": "config",
                "name": "配置一致性：source_iface",
                "status": "ok",
                "message": f"配置的 source_iface ({source_iface}) 存在",
            })
            append_log(state, "OK", f"检测项: 配置一致性：source_iface - 配置的 source_iface ({source_iface}) 存在")
    
    # 检查配置一致性：local_iface 是否存在（如果配置了）
    local_iface = cfg.get("local_iface")
    if local_iface:
        all_interfaces = get_all_interfaces()
        interface_names = [iface["name"] for iface in all_interfaces]
        if local_iface not in interface_names:
            items.append({
                "category": "config",
                "name": "配置一致性：local_iface",
                "status": "error",
                "message": f"配置的 local_iface ({local_iface}) 不存在",
            })
            append_log(state, "ERROR", f"检测项: 配置一致性：local_iface - 配置的 local_iface ({local_iface}) 不存在")
        else:
            items.append({
                "category": "config",
                "name": "配置一致性：local_iface",
                "status": "ok",
                "message": f"配置的 local_iface ({local_iface}) 存在",
            })
            append_log(state, "OK", f"检测项: 配置一致性：local_iface - 配置的 local_iface ({local_iface}) 存在")


def _check_services(cfg: Dict[str, Any], items: List[Dict[str, Any]], state: Dict[str, Any]) -> None:
    """系统服务检测"""
    # 检查 API 服务运行状态
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*api.main:app"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            items.append({
                "category": "services",
                "name": "API 服务运行状态",
                "status": "ok",
                "message": f"API 服务运行中 (PID: {', '.join(pids)})",
                "details": {"pids": pids},
            })
            append_log(state, "OK", f"检测项: API 服务运行状态 - API 服务运行中 (PID: {', '.join(pids)})")
        else:
            items.append({
                "category": "services",
                "name": "API 服务运行状态",
                "status": "error",
                "message": "API 服务未运行",
            })
            append_log(state, "ERROR", "检测项: API 服务运行状态 - API 服务未运行")
    except Exception as e:
        items.append({
            "category": "services",
            "name": "API 服务运行状态",
            "status": "warn",
            "message": f"检测失败: {str(e)}",
        })
        append_log(state, "WARN", f"检测项: API 服务运行状态 - 检测失败: {str(e)}")
    
    # 检查定时任务配置状态
    try:
        from .cron import get_cron_status
        cron_status = get_cron_status()
        if cron_status.get("enabled"):
            cron_expr = cron_status.get("cron_expr", "未知")
            items.append({
                "category": "services",
                "name": "定时任务配置状态",
                "status": "ok",
                "message": f"定时任务已配置 ({cron_expr})",
                "details": {"cron_expr": cron_expr},
            })
            append_log(state, "OK", f"检测项: 定时任务配置状态 - 定时任务已配置 ({cron_expr})")
        else:
            items.append({
                "category": "services",
                "name": "定时任务配置状态",
                "status": "warn",
                "message": "定时任务未配置",
            })
            append_log(state, "WARN", "检测项: 定时任务配置状态 - 定时任务未配置")
    except Exception as e:
        items.append({
            "category": "services",
            "name": "定时任务配置状态",
            "status": "warn",
            "message": f"检测失败: {str(e)}",
        })
        append_log(state, "WARN", f"检测项: 定时任务配置状态 - 检测失败: {str(e)}")
