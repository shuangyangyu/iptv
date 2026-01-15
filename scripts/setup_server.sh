#!/bin/bash
# -*- coding: utf-8 -*-
#
# 服务器环境准备脚本
# 在服务器上运行，用于检查环境、安装软件、创建虚拟环境和安装依赖

set -e

# ============================================================================
# 配置（从环境变量或默认值获取）
# ============================================================================

BASE_DIR="${BASE_DIR:-~/iptv_sever}"
VENV_DIR="${VENV_DIR:-$BASE_DIR/venv}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-$BASE_DIR/api/requirements.txt}"

# 展开 ~ 符号
BASE_DIR="${BASE_DIR/#\~/$HOME}"
VENV_DIR="${VENV_DIR/#\~/$HOME}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE/#\~/$HOME}"

# ============================================================================
# 日志函数
# ============================================================================

# 颜色输出
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# 环境检查函数
# ============================================================================

# 检查 Python3 是否存在
check_python3() {
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1)
        log_success "Python3 已安装: $python_version"
        return 0
    else
        log_warning "Python3 未安装"
        return 1
    fi
}

# 检查 pip 是否可用
check_pip() {
    # 优先检查 python3 -m pip
    if python3 -m pip --version >/dev/null 2>&1; then
        local pip_version=$(python3 -m pip --version 2>&1 | head -1)
        log_success "pip 已安装: $pip_version"
        return 0
    fi
    
    # 其次检查 ~/.local/bin/pip3（用户级安装）
    if [ -f ~/.local/bin/pip3 ] && ~/.local/bin/pip3 --version >/dev/null 2>&1; then
        local pip_version=$(~/.local/bin/pip3 --version 2>&1 | head -1)
        log_success "pip 已安装（用户级）: $pip_version"
        return 0
    fi
    
    log_warning "pip 未安装"
    return 1
}

# 检查虚拟环境是否存在
check_venv() {
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        log_success "虚拟环境已存在: $VENV_DIR"
        return 0
    else
        log_warning "虚拟环境不存在: $VENV_DIR"
        return 1
    fi
}

# 检查 UDPXY 是否已安装
check_udpxy() {
    # 首先尝试使用 which/command 查找
    local udpxy_path
    if udpxy_path=$(command -v udpxy 2>/dev/null); then
        # 验证文件确实存在且可执行
        if [ -f "$udpxy_path" ] && [ -x "$udpxy_path" ]; then
            # UDPXY 不支持 -h 选项，直接检查文件即可
            log_success "UDPXY 已安装: $udpxy_path"
            # 尝试获取文件信息
            if command -v file >/dev/null 2>&1; then
                local file_info
                file_info=$(file "$udpxy_path" 2>/dev/null | cut -d: -f2-)
                if [ -n "$file_info" ]; then
                    log_info "  $file_info"
                fi
            fi
            return 0
        fi
    fi
    
    # 检查常见路径（优先检查 /usr/local/bin，这是源码安装的默认位置）
    local common_paths=("/usr/local/bin/udpxy" "/usr/bin/udpxy" "/opt/local/bin/udpxy")
    for path in "${common_paths[@]}"; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            # UDPXY 不支持 -h 选项，直接检查文件即可
            log_success "UDPXY 已安装: $path"
            # 尝试获取文件信息
            if command -v file >/dev/null 2>&1; then
                local file_info
                file_info=$(file "$path" 2>/dev/null | cut -d: -f2-)
                if [ -n "$file_info" ]; then
                    log_info "  $file_info"
                fi
            fi
            # 如果不在 PATH 中，提示用户
            if ! command -v udpxy >/dev/null 2>&1; then
                log_info "  提示: 如果命令不可用，请确保 /usr/local/bin 在 PATH 中"
            fi
            return 0
        fi
    done
    
    log_warning "UDPXY 未安装"
    return 1
}

# ============================================================================
# 安装函数
# ============================================================================

# 安装 Python3
install_python3() {
    log_info "检测到 Python3 缺失，需要安装..."
    log_warning "安装 Python3 需要 sudo 权限"
    echo ""
    
    # 检测包管理器
    local install_cmd=""
    local package_manager=""
    
    if command -v apt-get >/dev/null 2>&1; then
        package_manager="apt-get"
        install_cmd="sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv"
    elif command -v yum >/dev/null 2>&1; then
        package_manager="yum"
        install_cmd="sudo yum install -y python3 python3-pip"
    elif command -v dnf >/dev/null 2>&1; then
        package_manager="dnf"
        install_cmd="sudo dnf install -y python3 python3-pip"
    elif command -v pacman >/dev/null 2>&1; then
        package_manager="pacman"
        install_cmd="sudo pacman -S --noconfirm python python-pip"
    else
        log_error "未检测到支持的包管理器"
        log_info "请手动安装 Python3:"
        log_info "  Debian/Ubuntu: sudo apt-get install -y python3 python3-pip python3-venv"
        log_info "  CentOS/RHEL: sudo yum install -y python3 python3-pip"
        log_info "  Fedora: sudo dnf install -y python3 python3-pip"
        log_info "  Arch Linux: sudo pacman -S --noconfirm python python-pip"
        return 1
    fi
    
    log_info "检测到 $package_manager，使用 $package_manager 安装 Python3..."
    log_warning "需要 sudo 权限，请输入密码（如果需要）:"
    echo ""
    
    # 尝试验证 sudo 权限
    if ! sudo -v 2>/dev/null; then
        log_error "无法获取 sudo 权限"
        log_info "请手动执行以下命令："
        log_info "  $install_cmd"
        return 1
    fi
    
    # 执行安装
    if eval "$install_cmd"; then
        log_success "Python3 安装成功"
        return 0
    else
        log_error "Python3 安装失败"
        log_info "请手动执行：$install_cmd"
        return 1
    fi
}

# 安装 pip
install_pip() {
    log_info "检测到 pip 缺失，尝试自动安装..."
    log_info "使用 get-pip.py 安装 pip（用户级安装，无需 sudo）..."
    
    # 检查是否有 curl 或 wget
    local has_curl=false
    local has_wget=false
    
    if command -v curl >/dev/null 2>&1; then
        has_curl=true
    elif command -v wget >/dev/null 2>&1; then
        has_wget=true
    else
        log_error "未找到 curl 或 wget，无法下载 get-pip.py"
        log_info "请手动安装 pip 或安装 curl/wget"
        return 1
    fi
    
    local install_output=""
    local install_status=1
    
    if [ "$has_curl" = "true" ]; then
        log_info "使用 curl 下载 get-pip.py..."
        install_output=$(curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
            python3 /tmp/get-pip.py --user --break-system-packages && \
            rm /tmp/get-pip.py 2>&1)
        install_status=$?
    elif [ "$has_wget" = "true" ]; then
        log_info "使用 wget 下载 get-pip.py..."
        install_output=$(wget -q -O /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py && \
            python3 /tmp/get-pip.py --user --break-system-packages && \
            rm /tmp/get-pip.py 2>&1)
        install_status=$?
    fi
    
    if [ $install_status -eq 0 ]; then
        log_success "pip 安装成功（使用 get-pip.py）"
        # 确保 ~/.local/bin 在 PATH 中
        if [ -d ~/.local/bin ] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            export PATH="$HOME/.local/bin:$PATH"
            log_info "已将 ~/.local/bin 添加到 PATH"
        fi
        return 0
    else
        log_error "pip 自动安装失败"
        log_error "安装输出: $install_output"
        log_info ""
        log_info "如果安装失败，可以尝试手动安装："
        log_info "  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py"
        log_info "  python3 get-pip.py --user --break-system-packages"
        return 1
    fi
}

# 安装 UDPXY
install_udpxy() {
    log_info "检测到 UDPXY 缺失，需要安装..."
    log_warning "安装 UDPXY 需要 sudo 权限"
    echo ""
    
    # 检测包管理器
    local install_cmd=""
    local package_manager=""
    
    if command -v opkg >/dev/null 2>&1; then
        package_manager="opkg"
        install_cmd="sudo opkg update && sudo opkg install udpxy"
    elif command -v apt-get >/dev/null 2>&1; then
        package_manager="apt-get"
        install_cmd="sudo apt-get update && sudo apt-get install -y udpxy"
    elif command -v yum >/dev/null 2>&1; then
        package_manager="yum"
        install_cmd="sudo yum install -y udpxy"
    elif command -v dnf >/dev/null 2>&1; then
        package_manager="dnf"
        install_cmd="sudo dnf install -y udpxy"
    elif command -v pacman >/dev/null 2>&1; then
        package_manager="pacman"
        install_cmd="sudo pacman -S --noconfirm udpxy"
    else
        log_error "未检测到支持的包管理器"
        log_info "请手动安装 UDPXY:"
        log_info "  OpenWrt: sudo opkg update && sudo opkg install udpxy"
        log_info "  Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y udpxy"
        log_info "  CentOS/RHEL: sudo yum install -y udpxy"
        log_info "  Fedora: sudo dnf install -y udpxy"
        log_info "  Arch Linux: sudo pacman -S --noconfirm udpxy"
        log_info ""
        log_info "或从源码编译安装:"
        log_info "  git clone https://github.com/pcherenkov/udpxy.git"
        log_info "  cd udpxy"
        log_info "  make"
        log_info "  sudo make install"
        return 1
    fi
    
    log_info "检测到 $package_manager，使用 $package_manager 安装 UDPXY..."
    log_warning "需要 sudo 权限，请输入密码（如果需要）:"
    echo ""
    
    # 尝试验证 sudo 权限
    if ! sudo -v 2>/dev/null; then
        log_error "无法获取 sudo 权限"
        log_info "请手动执行以下命令："
        log_info "  $install_cmd"
        return 1
    fi
    
    # 执行安装
    if eval "$install_cmd"; then
        log_success "UDPXY 安装成功"
        return 0
    else
        log_warning "包管理器安装失败，尝试从源码编译安装..."
        log_info "这需要 git 和 make 工具"
        echo ""
        
        # 检查并安装必要的工具
        local need_install_tools=false
        
        if ! command -v git >/dev/null 2>&1; then
            log_warning "未找到 git，需要安装"
            need_install_tools=true
        fi
        
        if ! command -v make >/dev/null 2>&1; then
            log_warning "未找到 make，需要安装 build-essential"
            need_install_tools=true
        fi
        
        # 如果需要安装工具，尝试自动安装
        if [ "$need_install_tools" = "true" ]; then
            log_info "尝试自动安装编译工具..."
            
            local tool_install_cmd=""
            if command -v apt-get >/dev/null 2>&1; then
                tool_install_cmd="sudo apt-get install -y git build-essential"
            elif command -v yum >/dev/null 2>&1; then
                tool_install_cmd="sudo yum install -y git gcc make"
            elif command -v dnf >/dev/null 2>&1; then
                tool_install_cmd="sudo dnf install -y git gcc make"
            elif command -v pacman >/dev/null 2>&1; then
                tool_install_cmd="sudo pacman -S --noconfirm git base-devel"
            else
                log_error "未检测到支持的包管理器，无法自动安装编译工具"
                log_info "请手动安装:"
                log_info "  Debian/Ubuntu: sudo apt-get install -y git build-essential"
                log_info "  CentOS/RHEL: sudo yum install -y git gcc make"
                log_info "  Fedora: sudo dnf install -y git gcc make"
                log_info "  Arch Linux: sudo pacman -S --noconfirm git base-devel"
                return 1
            fi
            
            log_info "执行: $tool_install_cmd"
            if ! eval "$tool_install_cmd" 2>&1; then
                log_error "编译工具安装失败"
                log_info "请手动执行: $tool_install_cmd"
                return 1
            fi
            
            log_success "编译工具安装成功"
            echo ""
        fi
        
        # 再次检查工具是否可用
        if ! command -v git >/dev/null 2>&1; then
            log_error "git 仍不可用，无法从源码编译"
            return 1
        fi
        
        if ! command -v make >/dev/null 2>&1; then
            log_error "make 仍不可用，无法从源码编译"
            return 1
        fi
        
        # 创建临时目录
        local build_dir="/tmp/udpxy_build_$$"
        log_info "创建临时构建目录: $build_dir"
        mkdir -p "$build_dir"
        
        # 克隆源码（带超时和重试）
        log_info "克隆 UDPXY 源码..."
        log_info "这可能需要一些时间，请耐心等待..."
        
        local clone_success=false
        local max_retries=3
        local retry_count=0
        
        while [ $retry_count -lt $max_retries ]; do
            if [ $retry_count -gt 0 ]; then
                log_info "重试克隆 (第 $retry_count/$max_retries 次)..."
            fi
            
            # 使用 timeout 命令限制克隆时间（5分钟超时）
            if command -v timeout >/dev/null 2>&1; then
                if timeout 300 git clone --progress https://github.com/pcherenkov/udpxy.git "$build_dir" 2>&1; then
                    clone_success=true
                    break
                else
                    local exit_code=$?
                    if [ $exit_code -eq 124 ]; then
                        log_warning "克隆超时（5分钟），正在重试..."
                    else
                        log_warning "克隆失败，正在重试..."
                    fi
                fi
            else
                # 如果没有 timeout 命令，直接尝试克隆
                if git clone --progress https://github.com/pcherenkov/udpxy.git "$build_dir" 2>&1; then
                    clone_success=true
                    break
                else
                    log_warning "克隆失败，正在重试..."
                fi
            fi
            
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                log_info "等待 3 秒后重试..."
                sleep 3
            fi
        done
        
        if [ "$clone_success" != "true" ]; then
            log_error "克隆源码失败（已重试 $max_retries 次）"
            log_info "可能的原因："
            log_info "  1. 网络连接问题"
            log_info "  2. GitHub 访问受限"
            log_info "  3. 防火墙阻止"
            log_info ""
            log_info "可以尝试手动克隆："
            log_info "  cd /tmp"
            log_info "  git clone https://github.com/pcherenkov/udpxy.git"
            log_info "  cd udpxy"
            log_info "  make"
            log_info "  sudo make install"
            rm -rf "$build_dir"
            return 1
        fi
        
        log_success "源码克隆成功"
        
        # 进入目录并查找 Makefile
        cd "$build_dir" || {
            log_error "无法进入构建目录"
            rm -rf "$build_dir"
            return 1
        }
        
        # 查找 Makefile（可能在子目录中）
        local makefile_path=""
        if [ -f "Makefile" ]; then
            makefile_path="."
        elif [ -f "udpxy/Makefile" ]; then
            makefile_path="udpxy"
        elif [ -d "chipmunk" ] && [ -f "chipmunk/Makefile" ]; then
            makefile_path="chipmunk"
        else
            # 尝试查找所有 Makefile
            makefile_path=$(find . -name "Makefile" -type f | head -1 | xargs dirname)
            if [ -z "$makefile_path" ]; then
                log_error "未找到 Makefile"
                log_info "目录内容："
                ls -la 2>&1 | head -20
                cd - >/dev/null 2>&1
                rm -rf "$build_dir"
                return 1
            fi
            makefile_path=$(echo "$makefile_path" | sed 's|^\./||')
        fi
        
        if [ "$makefile_path" != "." ]; then
            log_info "找到 Makefile 在子目录: $makefile_path"
            cd "$makefile_path" || {
                log_error "无法进入 Makefile 所在目录: $makefile_path"
                cd - >/dev/null 2>&1
                rm -rf "$build_dir"
                return 1
            }
        fi
        
        log_info "编译 UDPXY（在目录: $(pwd)）..."
        if ! make 2>&1; then
            log_error "编译失败"
            log_info "当前目录内容："
            ls -la 2>&1 | head -20
            cd - >/dev/null 2>&1
            rm -rf "$build_dir"
            return 1
        fi
        
        # 安装（需要 sudo）
        log_info "安装 UDPXY（需要 sudo 权限）..."
        if ! sudo make install 2>&1; then
            log_error "安装失败"
            cd - >/dev/null 2>&1
            rm -rf "$build_dir"
            return 1
        fi
        
        # 清理临时目录
        cd - >/dev/null 2>&1
        rm -rf "$build_dir"
        
        # 验证安装是否成功（直接检查文件，不依赖运行命令）
        # UDPXY 不支持 -h 选项，直接检查文件是否存在且可执行即可
        if [ -f "/usr/local/bin/udpxy" ] && [ -x "/usr/local/bin/udpxy" ]; then
            log_success "UDPXY 从源码编译安装成功"
            log_info "安装位置: /usr/local/bin/udpxy"
            # 确保 /usr/local/bin 在 PATH 中（仅当前会话）
            if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
                export PATH="/usr/local/bin:$PATH"
                log_info "已将 /usr/local/bin 添加到当前会话的 PATH"
            fi
            return 0
        fi
        
        log_warning "UDPXY 编译完成，但验证安装时出现问题"
        return 1
    fi
}

# 安装 python3-venv 包
install_python3_venv() {
    log_info "检测到需要安装 python3-venv 包..."
    log_warning "安装 python3-venv 需要 sudo 权限"
    echo ""
    
    # 获取 Python 版本号（如 3.12）
    local python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    log_info "检测到 Python 版本: $python_version"
    
    # 检测包管理器并安装对应的包
    local install_cmd=""
    local package_name=""
    
    if command -v apt-get >/dev/null 2>&1; then
        # Debian/Ubuntu: 先尝试安装特定版本包（如 python3.12-venv），失败则尝试通用包
        package_name="python${python_version}-venv"
        install_cmd="sudo apt-get install -y $package_name"
    elif command -v yum >/dev/null 2>&1; then
        package_name="python3-venv"
        install_cmd="sudo yum install -y $package_name"
    elif command -v dnf >/dev/null 2>&1; then
        package_name="python3-venv"
        install_cmd="sudo dnf install -y $package_name"
    elif command -v pacman >/dev/null 2>&1; then
        package_name="python"
        install_cmd="sudo pacman -S --noconfirm $package_name"
    else
        log_error "未检测到支持的包管理器"
        log_info "请手动安装 python3-venv:"
        log_info "  Debian/Ubuntu: sudo apt-get install -y python${python_version}-venv"
        return 1
    fi
    
    log_info "使用命令安装: $install_cmd"
    log_warning "需要 sudo 权限，请输入密码（如果需要）:"
    echo ""
    
    # 尝试验证 sudo 权限
    if ! sudo -v 2>/dev/null; then
        log_error "无法获取 sudo 权限"
        log_info "请手动执行以下命令："
        log_info "  $install_cmd"
        return 1
    fi
    
    # 执行安装
    if eval "$install_cmd" 2>&1; then
        log_success "python3-venv 安装成功"
        return 0
    else
        # 如果是 Debian/Ubuntu 且特定版本包安装失败，尝试通用包
        if command -v apt-get >/dev/null 2>&1 && [[ "$package_name" =~ python[0-9]+\.[0-9]+-venv ]]; then
            log_warning "特定版本包安装失败，尝试通用包..."
            package_name="python3-venv"
            install_cmd="sudo apt-get install -y $package_name"
            if eval "$install_cmd" 2>&1; then
                log_success "python3-venv 安装成功（使用通用包）"
                return 0
            fi
        fi
        log_error "python3-venv 安装失败"
        log_info "请手动执行：$install_cmd"
        return 1
    fi
}

# 创建虚拟环境
create_venv() {
    log_info "创建虚拟环境: $VENV_DIR"
    
    # 确保基础目录存在
    local base_dir=$(dirname "$VENV_DIR")
    if [ ! -d "$base_dir" ]; then
        log_info "创建基础目录: $base_dir"
        mkdir -p "$base_dir"
    fi
    
    # 尝试创建虚拟环境
    local venv_output
    venv_output=$(python3 -m venv "$VENV_DIR" 2>&1)
    local venv_status=$?
    
    if [ $venv_status -eq 0 ]; then
        log_success "虚拟环境创建成功: $VENV_DIR"
        return 0
    fi
    
    # 如果创建失败，检查是否是缺少 python3-venv 包
    if echo "$venv_output" | grep -qiE "(ensurepip|python3-venv|python.*-venv)"; then
        log_warning "虚拟环境创建失败，缺少 python3-venv 包"
        log_info "错误信息: $venv_output"
        echo ""
        
        # 尝试安装 python3-venv
        if install_python3_venv; then
            log_info "重新尝试创建虚拟环境..."
            # 清理之前失败的目录
            if [ -d "$VENV_DIR" ]; then
                rm -rf "$VENV_DIR"
            fi
            # 重新创建
            if python3 -m venv "$VENV_DIR" 2>&1; then
                log_success "虚拟环境创建成功: $VENV_DIR"
                return 0
            else
                log_error "安装 python3-venv 后仍无法创建虚拟环境"
                return 1
            fi
        else
            log_error "无法安装 python3-venv，虚拟环境创建失败"
            return 1
        fi
    else
        log_error "虚拟环境创建失败"
        log_error "错误信息: $venv_output"
        return 1
    fi
}

# ============================================================================
# 依赖安装函数
# ============================================================================

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    
    # 检查 requirements.txt 是否存在
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        log_error "requirements.txt 不存在: $REQUIREMENTS_FILE"
        log_info "请确保文件存在或设置 REQUIREMENTS_FILE 环境变量"
        return 1
    fi
    
    log_info "使用 requirements.txt: $REQUIREMENTS_FILE"
    
    # 激活虚拟环境并安装依赖
    if [ -f "$VENV_DIR/bin/activate" ]; then
        log_info "激活虚拟环境并安装依赖..."
        source "$VENV_DIR/bin/activate"
        
        # 升级 pip
        log_info "升级 pip..."
        pip install --upgrade pip --break-system-packages >/dev/null 2>&1 || true
        
        # 安装依赖
        log_info "安装依赖包..."
        if pip install --break-system-packages -r "$REQUIREMENTS_FILE"; then
            log_success "依赖安装成功"
            deactivate 2>/dev/null || true
            return 0
        else
            log_error "依赖安装失败"
            deactivate 2>/dev/null || true
            return 1
        fi
    else
        log_error "虚拟环境激活脚本不存在: $VENV_DIR/bin/activate"
        return 1
    fi
}

# ============================================================================
# 主流程
# ============================================================================

main() {
    log_info "=========================================="
    log_info "服务器环境准备"
    log_info "=========================================="
    echo ""
    log_info "配置信息："
    log_info "  基础目录: $BASE_DIR"
    log_info "  虚拟环境: $VENV_DIR"
    log_info "  依赖文件: $REQUIREMENTS_FILE"
    echo ""
    
    # 1. 检查并安装 Python3
    if ! check_python3; then
        if ! install_python3; then
            log_error "Python3 安装失败，退出"
            exit 1
        fi
        # 重新检查
        if ! check_python3; then
            log_error "Python3 安装后仍不可用，退出"
            exit 1
        fi
    fi
    echo ""
    
    # 2. 检查并安装 pip
    if ! check_pip; then
        if ! install_pip; then
            log_error "pip 安装失败，退出"
            exit 1
        fi
        # 重新检查
        if ! check_pip; then
            log_error "pip 安装后仍不可用，退出"
            exit 1
        fi
    fi
    echo ""
    
    # 3. 检查并创建虚拟环境
    if ! check_venv; then
        if ! create_venv; then
            log_error "虚拟环境创建失败，退出"
            exit 1
        fi
    fi
    echo ""
    
    # 4. 安装依赖
    if ! install_dependencies; then
        log_error "依赖安装失败，退出"
        exit 1
    fi
    echo ""
    
    # 5. 检查并安装 UDPXY
    if ! check_udpxy; then
        log_warning "UDPXY 未安装，这是可选的依赖"
        log_info "UDPXY 用于将组播流转换为 HTTP 流"
        log_info "如果不需要 UDPXY 功能，可以跳过安装"
        echo ""
        read -p "是否安装 UDPXY? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if ! install_udpxy; then
                log_warning "UDPXY 安装失败，但不影响其他功能"
            else
                # 重新检查
                if ! check_udpxy; then
                    log_warning "UDPXY 安装后仍不可用，但不影响其他功能"
                fi
            fi
        else
            log_info "跳过 UDPXY 安装"
        fi
    fi
    echo ""
    
    log_success "=========================================="
    log_success "环境准备完成！"
    log_success "=========================================="
    echo ""
    log_info "虚拟环境位置: $VENV_DIR"
    log_info "激活虚拟环境: source $VENV_DIR/bin/activate"
    log_info "退出虚拟环境: deactivate"
}

# 运行主函数
main "$@"
