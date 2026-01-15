#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
回放地址转换模块

功能：
- 检测和转换各种时间格式
- 构建回放URL
- 处理回放请求的地址转换
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from urllib.parse import quote


def detect_time_format(time_str: str) -> Optional[str]:
    """
    检测时间格式类型
    
    返回格式类型：
    - 'unix_seconds': Unix 时间戳（秒）
    - 'unix_millis': Unix 时间戳（毫秒）
    - 'iso8601': ISO 8601 格式 (YYYY-MM-DDTHH:MM:SSZ)
    - 'yyyy_mm_dd_hh_mm_ss': YYYYMMDDHHmmss 格式（无时区）
    - 'yyyy_mm_dd_hh_mm_ss_tz': YYYYMMDDHHmmss+00 格式（带时区）
    - None: 无法识别
    """
    time_str = time_str.strip()
    
    # 1. Unix 时间戳（秒）：10位数字
    if time_str.isdigit() and len(time_str) == 10:
        try:
            int(time_str)
            return 'unix_seconds'
        except ValueError:
            pass
    
    # 2. Unix 时间戳（毫秒）：13位数字
    if time_str.isdigit() and len(time_str) == 13:
        try:
            int(time_str)
            return 'unix_millis'
        except ValueError:
            pass
    
    # 3. ISO 8601 格式：YYYY-MM-DDTHH:MM:SSZ 或 YYYY-MM-DDTHH:MM:SS+00:00
    if 'T' in time_str or time_str.endswith('Z'):
        try:
            # 尝试解析 ISO 8601
            if time_str.endswith('Z'):
                dt = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
            elif '+' in time_str or time_str.count('-') >= 3:
                # 尝试解析带时区的 ISO 8601
                if '+' in time_str:
                    dt_str, tz_str = time_str.rsplit('+', 1)
                    dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
                else:
                    dt = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')
            return 'iso8601'
        except ValueError:
            pass
    
    # 4. YYYYMMDDHHmmss 格式（无时区）：14位数字
    if time_str.isdigit() and len(time_str) == 14:
        try:
            datetime.strptime(time_str, '%Y%m%d%H%M%S')
            return 'yyyy_mm_dd_hh_mm_ss'
        except ValueError:
            pass
    
    # 5. YYYYMMDDHHmmss+00 格式（带时区）：14位数字 + 时区后缀
    if len(time_str) >= 15 and time_str[:14].isdigit():
        if time_str[14:].startswith('+') or time_str[14:].startswith('-'):
            try:
                datetime.strptime(time_str[:14], '%Y%m%d%H%M%S')
                return 'yyyy_mm_dd_hh_mm_ss_tz'
            except ValueError:
                pass
    
    return None


def convert_to_zte_format(time_str: str, time_format: Optional[str] = None) -> str:
    """
    将各种时间格式转换为 ZTE_EPG16 需要的格式：YYYYMMDDHHmmss+00 (UTC)
    
    输入：
    - time_str: 时间字符串（各种格式）
    - time_format: 时间格式类型（可选，如果不提供会自动检测）
    
    返回：
    - str: YYYYMMDDHHmmss+00 格式的UTC时间字符串
    """
    if time_format is None:
        time_format = detect_time_format(time_str)
    
    if time_format is None:
        raise ValueError(f"无法识别时间格式: {time_str}")
    
    dt_utc: Optional[datetime] = None
    
    if time_format == 'unix_seconds':
        # Unix 时间戳（秒）→ UTC datetime
        dt_utc = datetime.fromtimestamp(int(time_str), tz=timezone.utc)
    
    elif time_format == 'unix_millis':
        # Unix 时间戳（毫秒）→ UTC datetime
        dt_utc = datetime.fromtimestamp(int(time_str) / 1000, tz=timezone.utc)
    
    elif time_format == 'iso8601':
        # ISO 8601 → UTC datetime
        time_str_clean = time_str.strip()
        if time_str_clean.endswith('Z'):
            dt_utc = datetime.strptime(time_str_clean, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        elif '+' in time_str_clean:
            # 带时区的 ISO 8601
            dt_str, tz_str = time_str_clean.rsplit('+', 1)
            dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
            # 解析时区偏移（简化处理，假设是 +HH:MM 或 +HHMM）
            tz_str = tz_str.replace(':', '')
            if len(tz_str) == 4:
                tz_hours = int(tz_str[:2])
                tz_mins = int(tz_str[2:])
                tz_offset = timedelta(hours=tz_hours, minutes=tz_mins)
                dt_utc = (dt.replace(tzinfo=timezone(tz_offset))).astimezone(timezone.utc)
            else:
                dt_utc = dt.replace(tzinfo=timezone.utc)
        else:
            # 无时区，假设是 UTC
            dt_utc = datetime.strptime(time_str_clean, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
    
    elif time_format == 'yyyy_mm_dd_hh_mm_ss':
        # YYYYMMDDHHmmss（无时区）→ 假设是本地时间（UTC+8），转换为 UTC
        dt_local = datetime.strptime(time_str, '%Y%m%d%H%M%S')
        # 假设是北京时间（UTC+8）
        tz_cn = timezone(timedelta(hours=8))
        dt_utc = dt_local.replace(tzinfo=tz_cn).astimezone(timezone.utc)
    
    elif time_format == 'yyyy_mm_dd_hh_mm_ss_tz':
        # YYYYMMDDHHmmss+00 → 解析时区并转换为 UTC
        if '+' in time_str:
            dt_str, tz_str = time_str.split('+', 1)
        elif '-' in time_str and time_str.count('-') == 1:
            dt_str, tz_str = time_str.split('-', 1)
            tz_str = '-' + tz_str
        else:
            dt_str = time_str[:14]
            tz_str = '+00'
        
        dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
        # 解析时区（简化处理，只处理 +00 或 -00）
        if tz_str.startswith('+') or tz_str.startswith('-'):
            tz_hours = int(tz_str[1:3]) if len(tz_str) >= 3 else 0
            tz_mins = int(tz_str[3:5]) if len(tz_str) >= 5 else 0
            tz_sign = -1 if tz_str.startswith('-') else 1
            tz_offset = timedelta(hours=tz_sign * tz_hours, minutes=tz_sign * tz_mins)
            dt_utc = dt.replace(tzinfo=timezone(tz_offset)).astimezone(timezone.utc)
        else:
            dt_utc = dt.replace(tzinfo=timezone.utc)
    
    if dt_utc is None:
        raise ValueError(f"无法转换时间格式: {time_str} (格式: {time_format})")
    
    # 格式化为 ZTE_EPG16 需要的格式：YYYYMMDDHHmmss+00
    return dt_utc.strftime('%Y%m%d%H%M%S+00')


def build_catchup_url(
    catchup_path: str,
    programbegin: str,
    programend: str,
    *,
    target_host: str = "10.255.129.26",
    target_port: int = 6060,
    virtual_domain: str = "hls.tvod_hls.zte.com",
    extra_params: Optional[Dict[str, str]] = None,
) -> str:
    """
    构建回放URL
    
    输入：
    - catchup_path: 回放路径（例如：ZTE_EPG16/2/9201）
    - programbegin: 开始时间（各种格式，会自动转换）
    - programend: 结束时间（各种格式，会自动转换）
    - target_host: 目标回放服务器地址（默认：10.255.129.26）
    - target_port: 目标回放服务器端口（默认：6060）
    - virtual_domain: 虚拟域名（默认：hls.tvod_hls.zte.com）
    - extra_params: 额外的查询参数（可选）
    
    返回：
    - str: 完整的回放URL
    """
    # 转换时间格式
    begin_zte = convert_to_zte_format(programbegin)
    end_zte = convert_to_zte_format(programend)
    
    # 构建查询参数
    query_params: Dict[str, str] = {}
    
    # 添加时间参数（手动编码+号为%2B）
    query_params['programbegin'] = begin_zte.replace('+', '%2B')
    query_params['programend'] = end_zte.replace('+', '%2B')
    
    # 添加virtualDomain参数
    query_params['virtualDomain'] = virtual_domain
    
    # 添加额外参数
    if extra_params:
        for key, value in extra_params.items():
            if key not in ('programbegin', 'programend', 'virtualDomain'):
                query_params[key] = value
    
    # 构建查询字符串
    query_parts = []
    for key, value in query_params.items():
        if key in ('programbegin', 'programend'):
            # 时间参数已经手动编码了+号
            query_parts.append(f"{key}={value}")
        else:
            # 其他参数使用quote编码
            encoded_value = quote(str(value), safe='')
            query_parts.append(f"{key}={encoded_value}")
    
    query_string = '&'.join(query_parts)
    
    # 构建完整URL
    target_url = f"http://{target_host}:{target_port}/{catchup_path}?{query_string}"
    
    return target_url


def convert_catchup_times(programbegin: str, programend: str) -> tuple[str, str]:
    """
    转换回放时间参数
    
    输入：
    - programbegin: 开始时间（各种格式）
    - programend: 结束时间（各种格式）
    
    返回：
    - tuple[str, str]: (转换后的开始时间, 转换后的结束时间) 格式为 YYYYMMDDHHmmss+00
    """
    begin_zte = convert_to_zte_format(programbegin)
    end_zte = convert_to_zte_format(programend)
    return (begin_zte, end_zte)

