#!/bin/bash
# -*- coding: utf-8 -*-
#
# SSH 密钥配置脚本
# 用于配置 SSH 密钥到服务器，支持清除现有配置并重新配置

# 加载配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# ============================================================================
# 配置管理函数组
# ============================================================================

# 显示服务器连接信息
show_server_info() {
    log_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warning "服务器连接信息："
    log_warning "  服务器地址: $SSH_HOST"
    log_warning "  SSH 用户: $SSH_USER"
    log_warning "  完整目标: $SSH_TARGET"
    log_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# 更新配置变量
update_config() {
    local new_host=$1
    local new_user=$2
    
    if [ -n "$new_host" ]; then
        SSH_HOST="$new_host"
    fi
    if [ -n "$new_user" ]; then
        SSH_USER="$new_user"
    fi
    SSH_TARGET="$SSH_USER@$SSH_HOST"
}

# 保存配置到文件
save_config_to_file() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS 使用 sed -i ''
        sed -i '' "s/^SSH_HOST=.*/SSH_HOST=\"$SSH_HOST\"/" "$SCRIPT_DIR/config.sh"
        sed -i '' "s/^SSH_USER=.*/SSH_USER=\"$SSH_USER\"/" "$SCRIPT_DIR/config.sh"
    else
        # Linux 使用 sed -i
        sed -i "s/^SSH_HOST=.*/SSH_HOST=\"$SSH_HOST\"/" "$SCRIPT_DIR/config.sh"
        sed -i "s/^SSH_USER=.*/SSH_USER=\"$SSH_USER\"/" "$SCRIPT_DIR/config.sh"
    fi
    log_success "配置已保存到 $SCRIPT_DIR/config.sh"
}

# 重新加载配置
load_config() {
    source "$SCRIPT_DIR/config.sh"
    log_info "配置已更新，重新加载配置..."
}

# ============================================================================
# 用户交互函数组
# ============================================================================

# 标准化 IP 地址（支持中文句号）
normalize_ip_address() {
    local input=$1
    local normalized
    
    # 将中文句号转换为英文点号
    normalized=$(echo "$input" | sed 's/。/./g')
    
    # 验证是否是有效的 IP 地址格式
    if [[ "$normalized" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo "$normalized"
        return 0
    fi
    
    return 1
}

# 提示输入服务器信息
prompt_for_server_info() {
    local default_host=$1
    local default_user=$2
    local new_host
    local new_user
    local original_input
    
    read -p "请输入服务器 IP 地址 [$default_host]: " new_host
    read -p "请输入 SSH 用户名 [$default_user]: " new_user
    
    # 标准化 IP 地址
    if [ -n "$new_host" ]; then
        original_input="$new_host"
        local normalized=$(normalize_ip_address "$new_host")
        if [ $? -eq 0 ]; then
            new_host="$normalized"
            # 如果原始输入包含中文句号，提示用户
            if [[ "$original_input" =~ 。 ]]; then
                log_info "检测到 IP 地址输入（已自动转换中文句号为英文点号）"
                log_info "原始输入: $original_input"
                log_info "转换后: $normalized"
                echo ""
            fi
        else
            log_error "IP 地址格式不正确: $new_host"
            return 1
        fi
    fi
    
    update_config "$new_host" "$new_user"
    return 0
}

# 确认并保存配置
confirm_and_save_config() {
    show_server_info
    
    read -p "是否保存到配置文件？(y/N): " save_config
    if [[ "$save_config" =~ ^[Yy]$ ]]; then
        save_config_to_file
    else
        log_info "配置未保存，仅本次使用"
    fi
    echo ""
    
    read -p "是否使用新配置继续？(y/N): " confirm2
    if [[ ! "$confirm2" =~ ^[Yy]$ ]]; then
        log_info "已取消操作"
        return 1
    fi
    echo ""
    return 0
}

# 查找可用编辑器
find_editor() {
    if [ -n "$EDITOR" ]; then
        echo "$EDITOR"
    elif command -v vim >/dev/null 2>&1; then
        echo "vim"
    elif command -v nano >/dev/null 2>&1; then
        echo "nano"
    elif command -v code >/dev/null 2>&1; then
        echo "code"
    else
        return 1
    fi
    return 0
}

# 编辑配置文件
edit_config_file() {
    log_info ""
    log_info "正在打开配置文件进行编辑..."
    log_info "配置文件: $SCRIPT_DIR/config.sh"
    echo ""
    
    local editor=$(find_editor)
    if [ $? -ne 0 ]; then
        log_error "未找到可用的编辑器"
        log_info "请手动编辑: $SCRIPT_DIR/config.sh"
        return 1
    fi
    
    log_info "使用编辑器: $editor"
    log_info "请修改以下配置项："
    log_info "  - SSH_HOST: 服务器 IP 地址"
    log_info "  - SSH_USER: SSH 用户名"
    log_info ""
    read -p "按回车键开始编辑..."
    
    "$editor" "$SCRIPT_DIR/config.sh"
    
    load_config
    show_server_info
    
    read -p "是否使用新配置继续？(y/N): " confirm2
    if [[ ! "$confirm2" =~ ^[Yy]$ ]]; then
        log_info "已取消操作"
        return 1
    fi
    echo ""
    return 0
}

# 处理用户输入
handle_user_input() {
    local confirm=$1
    
    # 智能识别：如果输入的是 IP 地址格式，自动进入输入模式
    local normalized=$(normalize_ip_address "$confirm")
    if [ $? -eq 0 ]; then
        # 用户直接输入了 IP 地址
        local new_host="$normalized"
        
        # 如果原始输入包含中文句号，提示用户
        if [[ "$confirm" =~ 。 ]]; then
            log_info "检测到 IP 地址输入（已自动转换中文句号为英文点号）"
            log_info "原始输入: $confirm"
            log_info "转换后: $new_host"
            echo ""
        fi
        
        if ! prompt_for_server_info "$new_host" "$SSH_USER"; then
            return 1
        fi
        
        if ! confirm_and_save_config; then
            return 1
        fi
        return 0
    fi
    
    # 处理其他选项
    case "$confirm" in
        [Yy])
            # 继续使用当前配置
            return 0
            ;;
        [Ii])
            # 直接输入 IP 地址
            log_info ""
            log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_info "直接输入服务器信息"
            log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            
            if ! prompt_for_server_info "$SSH_HOST" "$SSH_USER"; then
                return 1
            fi
            
            if ! confirm_and_save_config; then
                return 1
            fi
            return 0
            ;;
        [Ee])
            # 编辑配置文件
            if ! edit_config_file; then
                return 1
            fi
            return 0
            ;;
        *)
            # 取消操作
            log_info "已取消操作"
            log_info "如需修改服务器地址，请编辑: scripts/config.sh"
            return 1
            ;;
    esac
}

# ============================================================================
# SSH 操作函数组
# ============================================================================

# 检查 SSH 配置状态
check_ssh_config_status() {
    local status="not_configured"
    local ssh_configured=false
    local dropbear_configured=false
    
    # 获取公钥指纹（用于匹配）
    local pub_key_fingerprint=$(cat "$PUB_KEY_FILE" | cut -d" " -f2)
    
    # 检查标准 SSH 路径
    if ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        -o PasswordAuthentication=no \
        "$SSH_TARGET" "grep -Fq '$pub_key_fingerprint' ~/.ssh/authorized_keys 2>/dev/null" 2>/dev/null; then
        ssh_configured=true
    fi
    
    # 检查 dropbear 路径
    if ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        -o PasswordAuthentication=no \
        "$SSH_TARGET" "[ -d /etc/dropbear ] && grep -Fq '$pub_key_fingerprint' /etc/dropbear/authorized_keys 2>/dev/null" 2>/dev/null; then
        dropbear_configured=true
    fi
    
    # 返回状态
    if [ "$ssh_configured" = "true" ] || [ "$dropbear_configured" = "true" ]; then
        status="configured"
    fi
    
    # 输出详细状态（用于显示）
    echo "ssh_configured=$ssh_configured" >&2
    echo "dropbear_configured=$dropbear_configured" >&2
    
    echo "$status"
}

# 检查密钥是否已存在（简化版，用于快速检查）
check_key_exists() {
    local pub_key_fingerprint=$(cat "$PUB_KEY_FILE" | cut -d" " -f2)
    
    if ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        -o PasswordAuthentication=no \
        "$SSH_TARGET" "grep -Fq '$pub_key_fingerprint' ~/.ssh/authorized_keys 2>/dev/null" 2>/dev/null; then
        return 0
    fi
    return 1
}

# 从服务器移除 SSH 密钥
remove_ssh_key_from_server() {
    local pub_key_fingerprint=$(cat "$PUB_KEY_FILE" | cut -d" " -f2)
    # 转义特殊字符，用于 sed 正则表达式
    local escaped_fingerprint=$(echo "$pub_key_fingerprint" | sed 's/[[\.*^$()+?{|]/\\&/g')
    local ssh_result=0
    local dropbear_result=0
    local removed_count=0
    
    log_info "正在从服务器移除 SSH 密钥..."
    
    # 从标准 SSH 路径移除
    local remove_output
    local ssh_removed=0
    remove_output=$(ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        "$SSH_TARGET" "
        if [ -f ~/.ssh/authorized_keys ]; then
            # 检查删除前的行数
            before_count=\$(grep -c '$escaped_fingerprint' ~/.ssh/authorized_keys 2>/dev/null || echo 0)
            # 使用 grep -v 删除包含指纹的行（更安全，不依赖 sed 正则）
            grep -v '$escaped_fingerprint' ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp 2>/dev/null
            if [ \$? -eq 0 ]; then
                mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys
                echo \"\$before_count\"
            else
                echo \"0\"
            fi
        else
            echo \"0\"
        fi
    " 2>&1)
    ssh_result=$?
    
    # 提取删除的行数（只取数字）
    if [ $ssh_result -eq 0 ]; then
        ssh_removed=$(echo "$remove_output" | grep -E '^[0-9]+$' | head -1)
        if [ -z "$ssh_removed" ]; then
            ssh_removed=0
        fi
        removed_count=$((removed_count + ssh_removed))
        if [ $ssh_removed -gt 0 ]; then
            log_info "标准 SSH 路径: 删除了 $ssh_removed 行"
        fi
    fi
    
    # 从 dropbear 路径移除
    local dropbear_removed=0
    remove_output=$(ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        "$SSH_TARGET" "
        if [ -d /etc/dropbear ] && [ -f /etc/dropbear/authorized_keys ]; then
            before_count=\$(grep -c '$escaped_fingerprint' /etc/dropbear/authorized_keys 2>/dev/null || echo 0)
            grep -v '$escaped_fingerprint' /etc/dropbear/authorized_keys > /etc/dropbear/authorized_keys.tmp 2>/dev/null
            if [ \$? -eq 0 ]; then
                mv /etc/dropbear/authorized_keys.tmp /etc/dropbear/authorized_keys
                echo \"\$before_count\"
            else
                echo \"0\"
            fi
        else
            echo \"0\"
        fi
    " 2>&1)
    dropbear_result=$?
    
    # 提取删除的行数（只取数字）
    if [ $dropbear_result -eq 0 ]; then
        dropbear_removed=$(echo "$remove_output" | grep -E '^[0-9]+$' | head -1)
        if [ -z "$dropbear_removed" ]; then
            dropbear_removed=0
        fi
        removed_count=$((removed_count + dropbear_removed))
        if [ $dropbear_removed -gt 0 ]; then
            log_info "Dropbear 路径: 删除了 $dropbear_removed 行"
        fi
    fi
    
    # 验证删除结果
    if [ $removed_count -gt 0 ]; then
        log_success "SSH 密钥已从服务器移除（共删除 $removed_count 行）"
        return 0
    elif [ $ssh_result -eq 0 ] || [ $dropbear_result -eq 0 ]; then
        log_warning "删除操作执行成功，但未找到匹配的密钥（可能已经删除）"
        return 0
    else
        log_warning "移除操作可能失败，请检查服务器连接"
        return 1
    fi
}

# 提示是否清除现有配置
prompt_clear_existing_config() {
    local status_output=$(check_ssh_config_status 2>&1)
    local status=$(echo "$status_output" | tail -1)
    
    if [ "$status" != "configured" ]; then
        return 1  # 未配置，不需要清除
    fi
    
    # 解析状态信息
    local ssh_configured=$(echo "$status_output" | grep "ssh_configured=" | cut -d= -f2)
    local dropbear_configured=$(echo "$status_output" | grep "dropbear_configured=" | cut -d= -f2)
    
    log_warning "检测到 SSH 密钥已配置在服务器上"
    log_info "当前配置状态："
    if [ "$ssh_configured" = "true" ]; then
        log_info "  - ~/.ssh/authorized_keys: 已配置"
    else
        log_info "  - ~/.ssh/authorized_keys: 未配置"
    fi
    if [ "$dropbear_configured" = "true" ]; then
        log_info "  - /etc/dropbear/authorized_keys: 已配置"
    else
        log_info "  - /etc/dropbear/authorized_keys: 未配置"
    fi
    echo ""
    
    read -p "是否清除现有配置并重新配置？(y/N/c=取消): " clear_confirm
    case "$clear_confirm" in
        [Yy])
            return 0  # 清除
            ;;
        [Cc])
            log_info "已取消操作"
            return 2  # 取消
            ;;
        *)
            return 1  # 不清除
            ;;
    esac
}

# 清除 SSH 配置
clear_ssh_config() {
    log_info ""
    log_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warning "清除现有 SSH 配置"
    log_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warning "如果需要输入密码，请输入服务器 $SSH_USER@$SSH_HOST 的密码"
    echo ""
    
    if remove_ssh_key_from_server; then
        log_success "清除完成，可以重新配置"
        echo ""
        return 0
    else
        log_error "清除失败"
        return 1
    fi
}

# 使用 ssh-copy-id 配置密钥
configure_key_with_ssh_copy_id() {
    log_info "执行 ssh-copy-id（可能需要输入密码）..."
    log_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warning "如果现在提示输入密码，请输入服务器 $SSH_USER@$SSH_HOST 的密码"
    log_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    log_info "正在执行 ssh-copy-id..."
    log_info "如果密钥不存在，会提示输入密码；如果密钥已存在，则不会提示"
    echo ""
    
    if ssh-copy-id -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        "$SSH_TARGET"; then
        log_success "使用 ssh-copy-id 成功配置密钥"
        return 0
    else
        log_warning "ssh-copy-id 失败，尝试手动配置..."
        return 1
    fi
}

# 手动配置密钥
configure_key_manually() {
    log_info ""
    log_info "手动配置密钥到 $SSH_TARGET"
    log_warning "需要输入服务器 $SSH_USER@$SSH_HOST 的密码"
    log_info "如果这不是正确的服务器，请按 Ctrl+C 取消，然后编辑 scripts/config.sh"
    log_info ""
    
    local pub_key_fingerprint=$(cat "$PUB_KEY_FILE" | cut -d" " -f2)
    
    ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        "$SSH_TARGET" "
        # 确保 .ssh 目录存在
        mkdir -p ~/.ssh
        chmod 700 ~/.ssh
        
        # 添加公钥（如果不存在）
        if ! grep -Fq '$pub_key_fingerprint' ~/.ssh/authorized_keys 2>/dev/null; then
            echo '$PUB_KEY' >> ~/.ssh/authorized_keys
            echo '已添加到 ~/.ssh/authorized_keys'
        else
            echo '公钥已存在于 ~/.ssh/authorized_keys'
        fi
        chmod 600 ~/.ssh/authorized_keys
        
        # 配置 dropbear（OpenWrt 常用）
        if [ -d /etc/dropbear ]; then
            if ! grep -Fq '$pub_key_fingerprint' /etc/dropbear/authorized_keys 2>/dev/null; then
                echo '$PUB_KEY' >> /etc/dropbear/authorized_keys
                chmod 600 /etc/dropbear/authorized_keys
                echo '已添加到 /etc/dropbear/authorized_keys'
            else
                echo '公钥已存在于 /etc/dropbear/authorized_keys'
            fi
        fi
        
        echo ''
        echo '配置完成！'
    " 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "手动配置成功"
        return 0
    else
        log_error "手动配置失败"
        log_info ""
        log_info "请手动执行以下步骤："
        log_info "1. 登录服务器: ssh $SSH_TARGET"
        log_info "2. 创建目录: mkdir -p ~/.ssh && chmod 700 ~/.ssh"
        log_info "3. 添加公钥: echo '$PUB_KEY' >> ~/.ssh/authorized_keys"
        log_info "4. 设置权限: chmod 600 ~/.ssh/authorized_keys"
        return 1
    fi
}

# 测试 SSH 连接
test_ssh_connection() {
    log_info ""
    log_info "测试 SSH 连接..."
    if ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        "$SSH_TARGET" "echo 'SSH密钥登录成功！' && uname -a" 2>&1; then
        log_success "SSH 密钥配置成功！"
        log_info ""
        log_info "现在可以使用以下命令："
        log_info "  ./scripts/sync.sh        # 同步代码"
        log_info "  ./scripts/sync.sh all    # 同步代码到服务器"
        return 0
    else
        log_warning "SSH 连接测试失败，但配置可能已成功"
        log_info "请手动测试: ssh -i $SSH_KEY $SSH_TARGET"
        return 1
    fi
}

# 配置 SSH 密钥（主函数，整合所有配置方法）
configure_ssh_key() {
    # 先检查密钥是否已经存在
    if check_key_exists; then
        log_info "密钥已存在于服务器，跳过配置"
        return 0
    fi
    
    # 尝试使用 ssh-copy-id
    if command -v ssh-copy-id >/dev/null 2>&1; then
        if configure_key_with_ssh_copy_id; then
            return 0
        fi
    else
        log_warning "ssh-copy-id 不可用，使用手动配置..."
    fi
    
    # 使用手动配置
    if configure_key_manually; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# 主流程
# ============================================================================

# 检查前置条件
check_prerequisites() {
    if [ ! -f "$SSH_KEY" ]; then
        log_error "SSH 密钥文件不存在: $SSH_KEY"
        log_info "请确保密钥文件存在于以下位置之一："
        log_info "  - $PROJECT_ROOT/.ssh_router/router_key"
        log_info "  - $PROJECT_ROOT/.cursor_iptvhelper_ed25519"
        return 1
    fi
    
    PUB_KEY_FILE="${SSH_KEY}.pub"
    if [ ! -f "$PUB_KEY_FILE" ]; then
        log_error "公钥文件不存在: $PUB_KEY_FILE"
        log_info "请确保公钥文件存在"
        return 1
    fi
    
    PUB_KEY=$(cat "$PUB_KEY_FILE")
    return 0
}

# 主函数
main() {
    log_info "=========================================="
    log_info "配置 SSH 密钥到服务器"
    log_info "=========================================="
    echo ""
    log_info "私钥: $SSH_KEY"
    log_info "公钥: $PUB_KEY_FILE"
    echo ""
    
    # 1. 初始化检查
    if ! check_prerequisites; then
        exit 1
    fi
    
    # 2. 显示当前配置
    show_server_info
    
    # 3. 检查配置状态
    local status_output=$(check_ssh_config_status 2>&1)
    local config_status=$(echo "$status_output" | tail -1)
    
    # 4. 如果已配置，询问是否清除
    if [ "$config_status" = "configured" ]; then
        local clear_result
        prompt_clear_existing_config
        clear_result=$?
        
        case $clear_result in
            0)
                # 清除配置
                if ! clear_ssh_config; then
                    log_error "清除配置失败，退出"
                    exit 1
                fi
                ;;
            1)
                # 保持现有配置
                log_info "保持现有配置，退出"
                exit 0
                ;;
            2)
                # 取消操作
                log_info "已取消操作"
                exit 0
                ;;
        esac
    fi
    
    # 5. 处理用户输入（修改服务器信息）
    log_info "请确认这是正确的服务器地址！"
    read -p "是否继续？(y/N/e=编辑配置/i=直接输入IP，或直接输入IP地址): " confirm
    
    if ! handle_user_input "$confirm"; then
        exit 0
    fi
    
    # 6. 配置 SSH 密钥
    echo ""
    log_warning "即将连接到服务器，如果需要输入密码，请输入服务器 $SSH_USER@$SSH_HOST 的密码"
    log_info "如果这不是正确的服务器，请按 Ctrl+C 取消"
    echo ""
    
    log_info "方法1: 尝试使用 ssh-copy-id 配置密钥到 $SSH_TARGET"
    log_info "如果提示输入密码，请输入服务器 $SSH_USER@$SSH_HOST 的密码"
    echo ""
    
    if ! configure_ssh_key; then
        log_error "SSH 密钥配置失败"
        exit 1
    fi
    
    # 7. 测试连接
    test_ssh_connection
}

# 运行主函数
main "$@"
