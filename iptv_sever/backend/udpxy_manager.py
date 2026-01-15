#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UDPXY 进程管理
"""

import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class UdpxyManager:
    """UDPXY 服务管理器"""
    
    def __init__(self, config: Dict):
        """
        初始化 UDPXY 管理器
        
        Args:
            config: UDPXY 配置字典
        """
        self.config = config
        self.process = None
        self.pid_file = Path(config.get("pid_file", "/tmp/udpxy.pid"))
        self.udpxy_binary = self._find_udpxy()
    
    def _find_udpxy(self) -> Optional[str]:
        """查找系统 UDPXY 程序路径"""
        common_paths = ["udpxy", "/usr/bin/udpxy", "/usr/local/bin/udpxy"]
        for path in common_paths:
            if shutil.which(path):
                return path
        return None
    
    def check_available(self) -> Tuple[bool, str]:
        """
        检查 UDPXY 是否可用
        
        Returns:
            (是否可用, 消息)
        """
        if not self.udpxy_binary:
            return False, "未找到 UDPXY 程序，请先安装 udpxy"
        return True, "UDPXY 可用"
    
    def start(self) -> Tuple[bool, str, Optional[int]]:
        """
        启动 UDPXY 进程
        
        Returns:
            (是否成功, 消息, PID)
        """
        if not self.udpxy_binary:
            return False, "UDPXY 程序未安装", None
        
        # 检查是否有其他 UDPXY 进程在运行（通过端口检查）
        if self.is_running():
            return False, "UDPXY 已在运行", None
        
        # 检查端口是否被占用（可能是其他进程）
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((self.config["bind_address"], self.config["port"]))
            sock.close()
            if result == 0:
                # 端口被占用，尝试停止占用端口的进程
                try:
                    # 查找占用端口的进程
                    result = subprocess.run(
                        ["lsof", "-ti", f":{self.config['port']}"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        old_pid = int(result.stdout.strip())
                        try:
                            os.kill(old_pid, signal.SIGTERM)
                            time.sleep(1)
                        except (ProcessLookupError, OSError):
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        
        # 构建 udpxy 命令参数
        cmd = [
            self.udpxy_binary,
            "-p", str(self.config["port"]),
            "-a", self.config["bind_address"],
            "-m", self.config["source_iface"],
            "-c", str(self.config["max_connections"]),
        ]
        
        # 检查日志文件权限，如果无法写入则不使用日志文件
        log_file = self.config.get("log_file")
        if log_file:
            log_path = Path(log_file)
            log_dir = log_path.parent
            # 检查目录是否存在且可写，或者可以创建
            try:
                if not log_dir.exists():
                    log_dir.mkdir(parents=True, exist_ok=True)
                # 尝试创建测试文件
                test_file = log_dir / ".udpxy_test_write"
                try:
                    test_file.touch()
                    test_file.unlink()
                    # 可以写入，添加日志参数
                    cmd.extend(["-l", log_file])
                except (OSError, PermissionError):
                    # 无法写入，跳过日志文件
                    pass
            except (OSError, PermissionError):
                # 无法创建目录或写入，跳过日志文件
                pass
        
        # 启动进程
        try:
            # 在 Docker 容器中，使用 nohup 确保进程在后台运行
            # 使用 shell=True 和 nohup 命令，确保进程不会因为父进程退出而退出
            import shlex
            cmd_str = " ".join(shlex.quote(str(arg)) for arg in cmd)
            full_cmd = f"nohup {cmd_str} > /dev/null 2>&1 &"
            
            # 使用 shell 执行命令
            process = subprocess.Popen(
                full_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            process.wait()  # 等待 shell 命令完成
            
            # 等待进程启动（nohup 需要一些时间）
            time.sleep(1.0)  # 增加等待时间，确保进程完全启动
            
            # 尝试从端口监听状态找到 udpxy 进程
            max_retries = 15  # 增加重试次数
            pid = None
            for retry in range(max_retries):
                # 检查端口是否被监听（更可靠的方法）
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    result = sock.connect_ex((self.config["bind_address"], self.config["port"]))
                    sock.close()
                    if result == 0:
                        # 端口被监听，说明 udpxy 正在运行
                        # 尝试从 lsof 获取 PID（如果可用）
                        try:
                            result = subprocess.run(
                                ["lsof", "-ti", f":{self.config['port']}"],
                                capture_output=True,
                                text=True,
                                timeout=2,
                            )
                            if result.returncode == 0 and result.stdout.strip():
                                pid = int(result.stdout.strip())
                                break
                        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
                            # lsof 不可用或获取失败，尝试其他方法
                            # 使用 netstat 或 ss（如果可用）
                            try:
                                result = subprocess.run(
                                    ["ss", "-tlnp"],
                                    capture_output=True,
                                    text=True,
                                    timeout=2,
                                )
                                if result.returncode == 0:
                                    for line in result.stdout.split('\n'):
                                        if f":{self.config['port']}" in line and "udpxy" in line.lower():
                                            # 尝试从行中提取 PID
                                            import re
                                            match = re.search(r'pid=(\d+)', line)
                                            if match:
                                                pid = int(match.group(1))
                                                break
                            except Exception:
                                pass
                            # 如果还是找不到，使用端口检查确认进程存在即可
                            # PID 可以从后续的进程检查中获取
                except Exception:
                    pass
                
                # 如果还没找到，等待后重试
                if pid is None:
                    time.sleep(0.4)  # 增加等待时间
            
            if pid is None:
                # 如果无法获取 PID，但端口被监听，说明进程在运行
                # 等待更长时间，然后再次尝试获取 PID
                time.sleep(1.0)
                try:
                    result = subprocess.run(
                        ["lsof", "-ti", f":{self.config['port']}"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pid = int(result.stdout.strip().split('\n')[0])
                    else:
                        # 尝试通过进程名查找 PID
                        try:
                            result = subprocess.run(
                                ["pgrep", "-f", f"udpxy.*-p.*{self.config['port']}"],
                                capture_output=True,
                                text=True,
                                timeout=2,
                            )
                            if result.returncode == 0 and result.stdout.strip():
                                pid = int(result.stdout.strip().split('\n')[0])
                            else:
                                return False, "UDPXY 启动失败：无法确认进程是否运行", None
                        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
                            return False, "UDPXY 启动失败：无法确认进程是否运行", None
                except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
                    return False, "UDPXY 启动失败：无法确认进程是否运行", None
            
            # 保存 PID
            self.pid_file.write_text(str(pid))
            self.process = None  # 不使用 process 对象
            
            # 验证进程是否真的在运行
            try:
                os.kill(pid, 0)
            except OSError:
                return False, "UDPXY 进程启动后立即退出", None
            
            # 再次验证端口是否被监听（确保服务完全启动）
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.config["bind_address"], self.config["port"]))
                sock.close()
                if result != 0:
                    return False, "UDPXY 启动后端口未监听", None
            except Exception as e:
                logger.warning(f"验证端口监听失败: {e}")
            
            logger.info(f"UDPXY 启动成功，PID: {pid}, 端口: {self.config['port']}")
            return True, f"UDPXY 启动成功 (PID: {pid}, 端口: {self.config['port']})", pid
        except Exception as e:
            return False, f"启动失败: {str(e)}", None
    
    def stop(self) -> Tuple[bool, str]:
        """
        停止 UDPXY 进程
        
        Returns:
            (是否成功, 消息)
        """
        if not self.is_running():
            return False, "UDPXY 未运行"
        
        try:
            pid = int(self.pid_file.read_text())
            
            # 先尝试优雅停止（SIGTERM）
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                # 进程已经不存在
                if self.pid_file.exists():
                    self.pid_file.unlink()
                return False, "UDPXY 进程不存在"
            
            # 等待进程结束（最多等待 5 秒）
            import time
            max_wait = 5
            waited = 0
            while waited < max_wait:
                try:
                    # 使用 WNOHANG 非阻塞等待，避免无限等待
                    result = os.waitpid(pid, os.WNOHANG)
                    if result[0] == pid:
                        # 进程已退出
                        break
                except ChildProcessError:
                    # 子进程不是当前进程的子进程（因为我们用了 start_new_session）
                    # 尝试直接检查进程是否存在
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        # 进程已退出
                        break
                except OSError:
                    # 进程已退出
                    break
                
                time.sleep(0.1)
                waited += 0.1
            
            # 如果进程还在运行，强制停止
            try:
                os.kill(pid, 0)  # 检查进程是否还存在
                os.kill(pid, signal.SIGKILL)  # 强制终止
                time.sleep(0.5)
                # 再次尝试等待
                try:
                    os.waitpid(pid, os.WNOHANG)
                except (ChildProcessError, OSError):
                    pass
            except ProcessLookupError:
                pass  # 进程已经退出
            
            # 清理 PID 文件
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            return True, "UDPXY 停止成功"
        except ProcessLookupError:
            # 进程已经不存在
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False, "UDPXY 进程不存在"
        except Exception as e:
            return False, f"停止失败: {str(e)}"
    
    def is_running(self) -> bool:
        """
        检查 UDPXY 进程是否运行
        
        Returns:
            是否运行
        """
        # 首先检查端口是否被监听（更可靠的方法）
        # 在 Docker host 网络模式下，udpxy 监听主机的网络接口
        # 尝试多种方式检查端口
        port_listening = False
        try:
            # 方法1: 尝试连接本地端口
            for addr in ["127.0.0.1", "0.0.0.0", "localhost"]:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.3)
                    result = sock.connect_ex((addr, self.config["port"]))
                    sock.close()
                    if result == 0:
                        port_listening = True
                        break
                except Exception:
                    continue
        except Exception:
            pass
        
        # 方法2: 使用 lsof 检查端口（如果可用）
        if not port_listening:
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{self.config['port']}"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    port_listening = True
            except Exception:
                pass
        
        if port_listening:
            # 端口被监听，说明 udpxy 正在运行
            # 尝试更新 PID 文件
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{self.config['port']}"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    pid = int(result.stdout.strip().split('\n')[0])
                    # 更新 PID 文件
                    self.pid_file.write_text(str(pid))
                    logger.debug(f"UDPXY 端口检测成功，PID: {pid}")
                    return True
            except Exception as e:
                logger.debug(f"获取 PID 失败: {e}")
                pass
            # 即使无法获取 PID，端口被监听也说明服务在运行
            logger.debug("UDPXY 端口检测成功，但无法获取 PID")
            return True
        
        # 如果端口检查失败，检查 PID 文件
        if not self.pid_file.exists():
            return False
        
        try:
            pid = int(self.pid_file.read_text())
            os.kill(pid, 0)  # 检查进程是否存在（不发送信号）
            return True
        except (OSError, ValueError):
            return False
    
    def get_status(self) -> Dict:
        """
        获取 UDPXY 状态
        
        Returns:
            状态字典
        """
        available, msg = self.check_available()
        running = self.is_running()
        
        status = {
            "running": running,
            "pid": None,
            "port": self.config["port"],
            "bind_address": self.config["bind_address"],
            "source_iface": self.config["source_iface"],
            "max_connections": self.config["max_connections"],
            "connections": 0,  # 初始化 connections 字段
            "uptime": 0,
            "available": available,
        }
        
        if running:
            try:
                pid = int(self.pid_file.read_text())
                status["pid"] = pid
            except Exception:
                pass
            
            # 从 UDPXY 状态接口获取连接数和运行时间
            try:
                port = self.config["port"]
                bind_address = self.config["bind_address"]
                
                # 构建状态 URL，如果 bind_address 是 0.0.0.0，使用 127.0.0.1
                if bind_address == "0.0.0.0":
                    status_url = f"http://127.0.0.1:{port}/status"
                else:
                    status_url = f"http://{bind_address}:{port}/status"
                
                # 请求状态接口（设置较短的超时时间，避免阻塞）
                req = urllib.request.Request(
                    status_url,
                    headers={"User-Agent": "iptv_sever_udpxy_manager"}
                )
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.getcode() == 200:
                        content = resp.read().decode('utf-8', errors='ignore')
                        
                        # UDPXY 状态接口可能返回 HTML 或纯文本格式
                        # 先尝试简单的数字匹配（适用于大多数格式）
                        
                        # 提取运行时间（秒）- 匹配 "uptime: 12345 s" 或类似格式
                        uptime_patterns = [
                            r'uptime[^:]*:\s*(\d+)\s*s',  # 纯文本格式
                            r'<td[^>]*>\s*Uptime[^<]*:</td>\s*<td[^>]*>(\d+)\s*s',  # HTML 表格
                            r'Uptime[^<]*:\s*<td[^>]*>(\d+)\s*s',  # HTML 变体
                        ]
                        for pattern in uptime_patterns:
                            uptime_match = re.search(pattern, content, re.IGNORECASE)
                            if uptime_match:
                                try:
                                    status["uptime"] = int(uptime_match.group(1))
                                    break
                                except (ValueError, IndexError):
                                    continue
                        
                        # 提取当前活跃连接数 - 尝试多种格式
                        # 方法1: 直接搜索数字（在 "active connections" 或 "connections" 附近）
                        connection_patterns = [
                            # 纯文本格式
                            r'active\s+connections?[^:]*:\s*(\d+)',
                            r'Active\s+connections?[^:]*:\s*(\d+)',
                            r'connections?[^:]*:\s*(\d+)',  # 更通用的匹配
                            # HTML 格式 - 更灵活的匹配
                            r'<td[^>]*>.*?[Aa]ctive\s+[Cc]onnections?.*?</td>\s*<td[^>]*>(\d+)',
                            r'<td[^>]*>(\d+)</td>\s*<td[^>]*>.*?[Aa]ctive\s+[Cc]onnections?',
                            r'Active\s+connections?.*?<td[^>]*>(\d+)',
                            # 尝试匹配任何包含 "connection" 和数字的格式
                            r'connection[^>]*>(\d+)<',
                            r'connection[^:]*:.*?(\d+)',
                        ]
                        for pattern in connection_patterns:
                            conn_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                            if conn_match:
                                try:
                                    conn_value = int(conn_match.group(1))
                                    if conn_value > 0 or status["connections"] == 0:
                                        status["connections"] = conn_value
                                    break
                                except (ValueError, IndexError):
                                    continue
                        
                        # 如果还没找到连接数，尝试 total connections
                        if status["connections"] == 0:
                            total_patterns = [
                                r'total\s+connections?[^:]*:\s*(\d+)',
                                r'<td[^>]*>.*?[Tt]otal\s+[Cc]onnections?.*?</td>\s*<td[^>]*>(\d+)',
                            ]
                            for pattern in total_patterns:
                                total_match = re.search(pattern, content, re.IGNORECASE)
                                if total_match:
                                    try:
                                        status["connections"] = int(total_match.group(1))
                                        break
                                    except (ValueError, IndexError):
                                        continue
                        
                        # 调试：记录响应内容（用于调试）
                        logger.debug(f"UDPXY 状态 URL: {status_url}")
                        logger.debug(f"UDPXY 状态响应内容（前1000字符）: {content[:1000]}")
                        logger.debug(f"解析结果 - connections: {status['connections']}, uptime: {status['uptime']}")
            except Exception as e:
                # 如果获取状态失败，记录但不影响其他状态信息
                # 连接数和运行时间保持默认值 0
                logger.warning(f"获取 UDPXY 状态失败: {e}", exc_info=True)
                pass
        
        return status

