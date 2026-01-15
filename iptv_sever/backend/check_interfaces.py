#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口检测脚本
用于检测M3U和EPG接口的可用性
"""

import sys
import json
import os
from pathlib import Path

# 允许直接运行脚本：把仓库根目录加入 sys.path
if __package__ in (None, ""):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

import urllib.request
from iptv_sever.backend.net import build_opener, get_ipv4_from_iface


def check_interface(url, source_iface, timeout):
    """检测单个接口"""
    if not url:
        return {"status": "skip", "message": "未配置接口"}
    
    try:
        # 获取源IP地址
        source_ip = get_ipv4_from_iface(source_iface) if source_iface else ""
        
        # 构建opener（绑定源IP）
        opener = build_opener(source_ip)
        
        # 发起请求
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0.0"})
        with opener.open(req, timeout=timeout) as resp:
            http_code = resp.getcode()
            content = resp.read()
            size = len(content) if content else 0
            
            if http_code == 200:
                return {
                    "status": "success",
                    "http_code": http_code,
                    "size": size,
                    "message": "接口正常"
                }
            else:
                return {
                    "status": "error",
                    "http_code": http_code,
                    "message": f"HTTP错误码: {http_code}"
                }
    except urllib.error.HTTPError as e:
        return {
            "status": "error",
            "http_code": e.code,
            "message": f"HTTP错误码: {e.code}"
        }
    except urllib.error.URLError as e:
        return {
            "status": "error",
            "http_code": 0,
            "message": f"连接失败: {str(e)[:100]}"
        }
    except Exception as e:
        return {
            "status": "error",
            "http_code": 0,
            "message": f"检测异常: {str(e)[:100]}"
        }


def main():
    # 获取参数
    m3u_url = sys.argv[1] if len(sys.argv) > 1 else ""
    epg_url = sys.argv[2] if len(sys.argv) > 2 else ""
    source_iface = sys.argv[3] if len(sys.argv) > 3 else "eth1"
    timeout = float(sys.argv[4]) if len(sys.argv) > 4 else 10.0
    
    # 检测接口
    m3u_result = check_interface(m3u_url, source_iface, timeout)
    epg_result = check_interface(epg_url, source_iface, timeout)
    
    # 输出JSON结果
    result = {
        "m3u": m3u_result,
        "epg": epg_result
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
