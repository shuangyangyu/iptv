#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络工具函数
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_interface_ip(iface: str) -> Optional[str]:
    """获取指定网卡的 IP 地址"""
    try:
        result = subprocess.run(
            ["ip", "addr", "show", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
            if ip_match:
                return ip_match.group(1)
    except Exception:
        pass
    
    try:
        result = subprocess.run(
            ["ifconfig", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
            if ip_match:
                return ip_match.group(1)
    except Exception:
        pass
    
    return None


def get_interface_gateway(iface: str) -> Optional[str]:
    """获取指定网卡的网关地址"""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "dev", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.split("\n"):
                gw_match = re.search(r"via\s+(\d+\.\d+\.\d+\.\d+)", line)
                if gw_match:
                    return gw_match.group(1)
    except Exception:
        pass
    
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.split("\n"):
                if iface in line:
                    gw_match = re.search(r"via\s+(\d+\.\d+\.\d+\.\d+)", line)
                    if gw_match:
                        return gw_match.group(1)
    except Exception:
        pass
    
    return None


def run_test_script(
    script_path,
    args: list,
    timeout: float,
    error_key: str = "error",
):
    """
    执行测试脚本并返回结果
    
    Returns:
        (success, result, error_message)
    """
    import json
    from pathlib import Path
    
    # 确保 script_path 是 Path 对象
    if script_path is None:
        return False, {error_key: {"status": "error", "message": "脚本路径为 None"}}, "脚本路径为 None"
    
    if not isinstance(script_path, Path):
        try:
            script_path = Path(script_path)
        except (TypeError, ValueError) as e:
            return False, {error_key: {"status": "error", "message": f"无效的脚本路径: {e}"}}, f"无效的脚本路径: {e}"
    
    if not script_path.exists():
        return False, {error_key: {"status": "error", "message": f"测试脚本不存在: {script_path}"}}, f"测试脚本不存在: {script_path}"
    
    # 确保 script_path.parent 存在且有效
    script_dir = script_path.parent
    if script_dir is None or not script_dir.exists():
        return False, {error_key: {"status": "error", "message": f"脚本目录不存在: {script_dir}"}}, f"脚本目录不存在: {script_dir}"
    
    try:
        if script_path.suffix == ".py":
            cmd = ["python3", str(script_path)] + args
        else:
            cmd = ["bash", str(script_path)] + args
        
        # 确保 cwd 是有效的字符串路径
        cwd_path = str(script_dir) if script_dir else None
        if cwd_path is None:
            return False, {error_key: {"status": "error", "message": "无法确定工作目录"}}, "无法确定工作目录"
        
        result = subprocess.run(
            cmd,
            cwd=cwd_path,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        
        if result.returncode == 0:
            try:
                test_result = json.loads(result.stdout)
                return True, test_result, None
            except json.JSONDecodeError:
                return False, {error_key: {"status": "error", "message": f"解析失败: {result.stdout[:100]}"}}, "解析失败"
        else:
            return False, {error_key: {"status": "error", "message": f"脚本执行失败: {result.stderr[:100]}"}}, "脚本执行失败"
    
    except subprocess.TimeoutExpired:
        return False, {error_key: {"status": "error", "message": "测试超时"}}, "测试超时"
    except Exception as e:
        return False, {error_key: {"status": "error", "message": str(e)}}, str(e)


def get_interface_status(iface: str) -> str:
    """获取接口状态"""
    try:
        result = subprocess.run(
            ["ip", "link", "show", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            if "state UP" in result.stdout or "state UNKNOWN" in result.stdout:
                return "up"
            else:
                return "down"
    except Exception:
        pass
    
    return "unknown"


def get_all_interfaces() -> List[Dict[str, Any]]:
    """获取所有网络接口列表（包括虚拟接口，但排除lo）"""
    interfaces = []
    seen_interfaces = set()  # 避免重复
    
    try:
        result = subprocess.run(
            ["ip", "link", "show"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                # 匹配格式: 1: interface_name: <...> 或 1: interface_name@xxx: <...>
                # 提取完整的接口名称（包括 @ 后面的部分，因为这是接口名称的一部分）
                # 使用 \S+ 匹配非空白字符（可以包含字母、数字、连字符、@ 等）
                match = re.search(r'^\d+:\s+(\S+):', line)
                if match:
                    # 如果接口名称包含 @，提取 @ 之前的部分作为主接口名称
                    full_name = match.group(1).strip()
                    if '@' in full_name:
                        interface_name = full_name.split('@')[0]
                    else:
                        interface_name = full_name
                    # 过滤掉 lo (loopback)
                    if interface_name != 'lo' and interface_name not in seen_interfaces:
                        seen_interfaces.add(interface_name)
                        ip = get_interface_ip(interface_name)
                        status = get_interface_status(interface_name)
                        # 尝试获取 MAC 地址和类型（不强制要求，失败时返回 None）
                        mac_address = get_mac_address(interface_name)
                        interface_type = get_interface_type(interface_name)
                        
                        interfaces.append({
                            "name": interface_name,
                            "status": status,
                            "ip": ip,
                            "has_ip": ip is not None,
                            "mac_address": mac_address,
                            "type": interface_type if interface_type else None,
                            # 其他字段在 physical_only=false 时不需要
                            "pic_id": None,
                            "driver": None,
                            "speed": None,
                            "duplex": None,
                        })
    except Exception as e:
        # 记录错误但不抛出异常
        import logging
        logging.warning(f"获取网络接口列表时出错: {e}")
        pass
    
    # 如果 ip 命令失败或没有获取到接口，尝试 ifconfig 作为备选
    if not interfaces:
        try:
            result = subprocess.run(
                ["ifconfig", "-a"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    # 匹配格式: interface_name: flags=...
                    match = re.search(r'^([^:\s]+):', line)
                    if match:
                        interface_name = match.group(1).strip()
                        if interface_name != 'lo' and interface_name not in seen_interfaces:
                            seen_interfaces.add(interface_name)
                            ip = get_interface_ip(interface_name)
                            status = get_interface_status(interface_name)
                            # 尝试获取 MAC 地址和类型（不强制要求，失败时返回 None）
                            mac_address = get_mac_address(interface_name)
                            interface_type = get_interface_type(interface_name)
                            
                            interfaces.append({
                                "name": interface_name,
                                "status": status,
                                "ip": ip,
                                "has_ip": ip is not None,
                                "mac_address": mac_address,
                                "type": interface_type if interface_type else None,
                                # 其他字段在 physical_only=false 时不需要
                                "pic_id": None,
                                "driver": None,
                                "speed": None,
                                "duplex": None,
                            })
        except Exception as e:
            import logging
            logging.warning(f"使用 ifconfig 获取网络接口列表时出错: {e}")
            pass
    
    return interfaces


def is_physical_interface(iface: str) -> bool:
    """判断接口是否为物理网卡"""
    # 虚拟接口特征列表
    virtual_keywords = ['lo', 'docker', 'br-', 'veth', 'virbr', 'vmnet', 'vboxnet', 'wlan-sta', 'tun', 'tap']
    
    # 检查接口名称是否包含虚拟接口特征
    for keyword in virtual_keywords:
        if keyword in iface:
            return False
    
    # 检查 /sys/class/net/<iface>/device 是否存在
    # 物理网卡通常有这个符号链接指向物理设备
    device_path = Path(f"/sys/class/net/{iface}/device")
    if device_path.exists() and device_path.is_symlink():
        try:
            resolved_path = device_path.resolve()
            if resolved_path.is_dir():
                return True
        except Exception:
            pass
    
    # 检查是否有 type 文件，且类型为物理网卡
    type_path = Path(f"/sys/class/net/{iface}/type")
    if type_path.exists():
        try:
            with open(type_path, 'r') as f:
                interface_type = int(f.read().strip())
                # 1 = ARPHRD_ETHER (以太网)
                # 801 = ARPHRD_IEEE80211 (无线网卡)
                if interface_type in (1, 801):
                    return True
        except Exception:
            pass
    
    return False


def get_mac_address(iface: str) -> Optional[str]:
    """获取网卡的MAC地址"""
    try:
        mac_path = Path(f"/sys/class/net/{iface}/address")
        if mac_path.exists():
            with open(mac_path, 'r') as f:
                mac = f.read().strip()
                # 验证MAC地址格式
                if re.match(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$', mac):
                    return mac
    except Exception:
        pass
    
    try:
        result = subprocess.run(
            ["ip", "link", "show", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            mac_match = re.search(
                r'link/ether\s+([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})',
                result.stdout
            )
            if mac_match:
                return mac_match.group(1)
    except Exception:
        pass
    
    return None


def get_pic_id(iface: str) -> Optional[str]:
    """获取物理接口卡的ID（PCI地址等）"""
    try:
        # 方法1: 通过 /sys/class/net/<iface>/device 获取PCI地址
        device_path = Path(f"/sys/class/net/{iface}/device")
        if device_path.exists() and device_path.is_symlink():
            try:
                real_path = device_path.resolve()
                # 提取PCI地址，格式如 0000:01:00.0
                pci_match = re.search(r'(\d{4}:\d{2}:\d{2}\.\d)', str(real_path))
                if pci_match:
                    return pci_match.group(1)
                
                # 检查是否是USB设备
                if 'usb' in str(real_path).lower():
                    usb_match = re.search(r'usb\d+/(\d+-\d+)', str(real_path))
                    if usb_match:
                        return f"usb-{usb_match.group(1)}"
            except Exception:
                pass
    except Exception:
        pass
    
    try:
        # 方法2: 使用 ethtool 获取PCI地址
        result = subprocess.run(
            ["ethtool", "-i", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            bus_info_match = re.search(r'bus-info:\s+(\S+)', result.stdout)
            if bus_info_match:
                return bus_info_match.group(1)
    except Exception:
        pass
    
    return None


def get_interface_type(iface: str) -> str:
    """获取网卡类型（ethernet 或 wireless）"""
    try:
        type_path = Path(f"/sys/class/net/{iface}/type")
        if type_path.exists():
            with open(type_path, 'r') as f:
                interface_type = int(f.read().strip())
                if interface_type == 1:  # ARPHRD_ETHER
                    return "ethernet"
                elif interface_type == 801:  # ARPHRD_IEEE80211
                    return "wireless"
    except Exception:
        pass
    
    # 通过名称判断（备用方法）
    if iface.startswith('wlan') or iface.startswith('wifi'):
        return "wireless"
    else:
        return "ethernet"


def get_interface_driver(iface: str) -> Optional[str]:
    """获取网卡驱动名称"""
    try:
        # 方法1: 通过 /sys/class/net/<iface>/device/driver 获取
        driver_path = Path(f"/sys/class/net/{iface}/device/driver")
        if driver_path.exists() and driver_path.is_symlink():
            try:
                return driver_path.resolve().name
            except Exception:
                pass
    except Exception:
        pass
    
    try:
        # 方法2: 使用 ethtool 获取驱动名称
        result = subprocess.run(
            ["ethtool", "-i", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            driver_match = re.search(r'driver:\s+(\S+)', result.stdout)
            if driver_match:
                return driver_match.group(1)
    except Exception:
        pass
    
    return None


def get_interface_speed_duplex(iface: str) -> Tuple[Optional[str], Optional[str]]:
    """获取网卡速度和双工模式"""
    try:
        result = subprocess.run(
            ["ethtool", iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            speed_match = re.search(r'Speed:\s+(\S+)', result.stdout)
            duplex_match = re.search(r'Duplex:\s+(\S+)', result.stdout)
            
            speed = speed_match.group(1) if speed_match else None
            duplex = duplex_match.group(1).lower() if duplex_match else None
            
            return speed, duplex
    except Exception:
        pass
    
    # 尝试从 /sys/class/net/<iface>/speed 读取（某些驱动支持）
    try:
        speed_path = Path(f"/sys/class/net/{iface}/speed")
        if speed_path.exists():
            with open(speed_path, 'r') as f:
                speed_value = f.read().strip()
                if speed_value.isdigit():
                    speed = f"{speed_value}Mbps"
                    # 尝试读取双工模式
                    duplex_path = Path(f"/sys/class/net/{iface}/duplex")
                    duplex = None
                    if duplex_path.exists():
                        with open(duplex_path, 'r') as df:
                            duplex = df.read().strip().lower()
                    return speed, duplex
    except Exception:
        pass
    
    return None, None


def get_physical_interfaces() -> List[Dict[str, Any]]:
    """获取所有物理网卡列表（通过PIC识别）"""
    physical_interfaces = []
    
    # 先获取所有接口
    all_interfaces = get_all_interfaces()
    
    # 过滤出物理网卡
    for iface_info in all_interfaces:
        iface_name = iface_info["name"]
        
        if is_physical_interface(iface_name):
            # 获取PIC信息
            pic_id = get_pic_id(iface_name)
            mac_address = get_mac_address(iface_name)
            interface_type = get_interface_type(iface_name)
            driver = get_interface_driver(iface_name)
            speed, duplex = get_interface_speed_duplex(iface_name)
            
            # 如果无法获取PIC ID，使用MAC地址作为标识
            if not pic_id and mac_address:
                pic_id = mac_address
            
            physical_interfaces.append({
                "name": iface_name,
                "status": iface_info.get("status", "unknown"),
                "ip": iface_info.get("ip"),
                "has_ip": iface_info.get("has_ip", False),
                "pic_id": pic_id,
                "mac_address": mac_address,
                "type": interface_type,
                "driver": driver,
                "speed": speed,
                "duplex": duplex,
            })
    
    return physical_interfaces


def get_interface_detail(iface: str) -> Dict[str, Any]:
    """获取指定网络接口的详细信息"""
    # 获取基本信息
    ip = get_interface_ip(iface)
    gateway = get_interface_gateway(iface)
    status = get_interface_status(iface)
    mac_address = get_mac_address(iface)
    interface_type = get_interface_type(iface)
    
    # 尝试获取物理网卡的详细信息
    pic_id = None
    driver = None
    speed = None
    duplex = None
    
    if is_physical_interface(iface):
        pic_id = get_pic_id(iface)
        driver = get_interface_driver(iface)
        speed, duplex = get_interface_speed_duplex(iface)
        # 如果无法获取PIC ID，使用MAC地址作为标识
        if not pic_id and mac_address:
            pic_id = mac_address
    
    return {
        "name": iface,
        "status": status,
        "ip": ip,
        "gateway": gateway,
        "has_ip": ip is not None,
        "mac_address": mac_address,
        "type": interface_type if interface_type else None,
        "pic_id": pic_id,
        "driver": driver,
        "speed": speed,
        "duplex": duplex,
    }


def get_local_iface_ip(cfg: Dict[str, Any]) -> Optional[str]:
    """
    从 local_iface 获取 IP 地址（仅使用 local_iface，不考虑 source_iface）
    
    Args:
        cfg: 配置字典，应包含 local_iface 字段
    
    Returns:
        IP 地址字符串，如果 local_iface 不存在或获取失败返回 None
    """
    import logging
    logger = logging.getLogger(__name__)
    
    local_iface = cfg.get("local_iface")
    if not local_iface:
        logger.warning("local_iface 未配置，无法获取 IP 地址")
        return None
    
    try:
        ip = get_interface_ip(local_iface)
        if ip:
            logger.info(f"从 local_iface ({local_iface}) 获取到 IP 地址: {ip}")
            return ip
        else:
            logger.warning(f"从 local_iface ({local_iface}) 获取 IP 地址失败")
            return None
    except Exception as e:
        logger.error(f"从 local_iface ({local_iface}) 获取 IP 地址时发生异常: {e}")
        return None

