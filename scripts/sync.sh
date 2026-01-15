#!/bin/bash
# -*- coding: utf-8 -*-
#
# 代码同步脚本
# 将本地代码同步到服务器

set -e

# 加载配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# 同步函数
sync_directory() {
    local local_dir=$1
    local remote_dir=$2
    local name=$3
    
    if [ ! -d "$local_dir" ]; then
        log_warning "本地目录不存在: $local_dir，跳过"
        return 0
    fi
    
    log_info "同步 $name: $local_dir -> $remote_dir"
    
    # 确保远程目录存在
    # 在远程服务器上展开 ~ 符号
    log_info "检查并创建远程目录: $remote_dir"
    mkdir_output=$(remote_exec "
        remote_path=\"$remote_dir\"
        # 展开 ~ 符号为用户主目录
        remote_path=\${remote_path/#\~/\$HOME}
        if [ -d \"\$remote_path\" ]; then
            echo '目录已存在: '\$remote_path
        elif mkdir -p \"\$remote_path\" 2>&1; then
            echo '目录创建成功: '\$remote_path
        else
            echo '目录创建失败'
            echo '当前用户: '$(whoami)
            echo '尝试创建的路径: '\$remote_path
            echo 'HOME 目录: '\$HOME
            parent_dir=\$(dirname \"\$remote_path\")
            if ls -ld \"\$parent_dir\" >/dev/null 2>&1; then
                echo '父目录权限: '\$(ls -ld \"\$parent_dir\")
            else
                echo '无法访问父目录'
            fi
        fi
    " 2>&1)
    
    # 获取展开后的路径（用于 rsync）
    remote_dir_expanded=$(remote_exec "remote_path=\"$remote_dir\"; echo \${remote_path/#\~/\$HOME}" 2>/dev/null || echo "$remote_dir")
    
    if echo "$mkdir_output" | grep -q "目录创建失败"; then
        log_error "无法创建远程目录: $remote_dir"
        log_error "详细信息:"
        echo "$mkdir_output" | grep -v "^$" | while IFS= read -r line; do
            log_error "  $line"
        done
        log_error ""
        log_error "可能的原因："
        log_error "  1. 权限不足（/www 目录通常需要 root 权限）"
        log_error "  2. 父目录不存在"
        log_error "  3. 磁盘空间不足"
        log_info ""
        log_info "解决方案："
        log_info "  方案1: 使用 sudo 创建目录（推荐）"
        log_info "    ssh $SSH_TARGET 'sudo mkdir -p $remote_dir && sudo chown -R $SSH_USER:$SSH_USER $(dirname $remote_dir)'"
        log_info ""
        log_info "  方案2: 修改配置文件使用用户目录"
        log_info "    编辑 scripts/config.sh，将 SERVER_BASE_DIR 改为 ~/iptv_sever 或 /home/$SSH_USER/iptv_sever"
        return 1
    elif echo "$mkdir_output" | grep -q "目录已存在"; then
        log_info "远程目录已存在"
    elif echo "$mkdir_output" | grep -q "目录创建成功"; then
        log_success "远程目录创建成功"
    fi
    
    # 使用 rsync 同步
    # 排除虚拟环境、缓存文件等（不同步到服务器）
    log_info "正在同步..."
    local rsync_output
    # 临时禁用 set -e，避免 rsync 命令失败导致脚本退出
    set +e
    # 将 SSH 的警告信息重定向到 /dev/null，避免干扰 rsync
    rsync_output=$(rsync -avz --delete \
        --exclude-from="$PROJECT_ROOT/.syncignore" \
        --exclude='.git/' \
        --exclude='venv/' \
        --exclude='env/' \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        --exclude='.DS_Store' \
        --exclude='node_modules/' \
        -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR" \
        "$local_dir/" "$SSH_TARGET:$remote_dir_expanded/" \
        2>&1)
    local rsync_status=$?
    set -e
    
    # 如果 rsync 失败，显示详细错误
    if [ $rsync_status -ne 0 ]; then
        log_error "rsync 同步失败，错误信息："
        echo "$rsync_output" | grep -v "sending incremental" | grep -v "sent.*bytes" | grep -v "^$" || echo "$rsync_output"
        log_error "可能的原因："
        log_error "  1. SSH 连接失败（密钥未配置或需要密码）"
        log_error "  2. 远程目录权限问题"
        log_error "  3. 网络连接问题"
        log_info "建议：运行 ./setup_ssh.sh 配置 SSH 密钥"
    else
        # 成功时显示同步的文件信息（过滤掉不重要的信息）
        echo "$rsync_output" | grep -v "sending incremental" | grep -v "sent.*bytes" | grep -v "^$" | head -20 || true
    fi
    
    if [ $rsync_status -eq 0 ]; then
        log_success "$name 同步完成"
        return 0
    else
        log_error "$name 同步失败"
        return 1
    fi
}

# 主函数
main() {
    log_info "=========================================="
    log_info "开始同步代码到服务器"
    log_info "=========================================="
    echo ""
    
    # 检查 SSH 连接
    if ! check_ssh; then
        exit 1
    fi
    
    # 解析参数
    local target="${1:-all}"
    
    case "$target" in
        api)
            sync_directory "$LOCAL_API_DIR" "$SERVER_API_DIR" "API"
            ;;
        backend)
            sync_directory "$LOCAL_BACKEND_DIR" "$SERVER_BACKEND_DIR" "Backend"
            ;;
        tests)
            sync_directory "$LOCAL_TESTS_DIR" "$SERVER_TESTS_DIR" "Tests"
            ;;
        frontend)
            # 前端需要先构建
            log_info "前端需要先构建，请运行: cd iptv_sever/frontend && npm run build"
            if [ -d "$LOCAL_FRONTEND_DIR/dist" ]; then
                sync_directory "$LOCAL_FRONTEND_DIR/dist" "$SERVER_FRONTEND_DIR/dist" "Frontend (dist)"
            else
                log_warning "前端构建目录不存在，跳过"
            fi
            ;;
        setup_server)
            log_info "同步环境准备脚本到服务器..."
            log_info "源文件: $SCRIPT_DIR/setup_server.sh"
            log_info "目标: $SSH_TARGET:$SERVER_BASE_DIR/setup_server.sh"
            echo ""
            
            # 检查源文件是否存在
            if [ ! -f "$SCRIPT_DIR/setup_server.sh" ]; then
                log_error "源文件不存在: $SCRIPT_DIR/setup_server.sh"
                exit 1
            fi
            
            # 同步脚本到服务器
            local rsync_output
            rsync_output=$(rsync -avz \
                --exclude='.git/' \
                -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
                "$SCRIPT_DIR/setup_server.sh" \
                "$SSH_TARGET:$SERVER_BASE_DIR/setup_server.sh" \
                2>&1)
            local rsync_status=$?
            
            # 清理输出
            rsync_output=$(echo "$rsync_output" | grep -v "Warning: Permanently added" | grep -v "sending incremental" | grep -v "sent.*bytes" | grep -v "^$" || true)
            
            if [ $rsync_status -eq 0 ]; then
                log_success "脚本已同步到服务器"
                echo ""
                log_info "使用方法："
                log_info "  1. SSH 到服务器: ssh $SSH_TARGET"
                log_info "  2. 执行脚本: bash $SERVER_BASE_DIR/setup_server.sh"
                log_info ""
                log_info "或者直接执行:"
                log_info "  ssh $SSH_TARGET 'bash $SERVER_BASE_DIR/setup_server.sh'"
            else
                log_error "脚本同步失败"
                echo "$rsync_output"
                exit 1
            fi
            ;;
        start_scripts)
            log_info "同步服务管理脚本到服务器..."
            echo ""
            
            # 检查源文件是否存在
            local scripts=("server_start.sh" "server_stop.sh" "server_restart.sh" "server_status.sh")
            local server_names=("start.sh" "stop.sh" "restart.sh" "status.sh")
            local missing_files=()
            
            for script in "${scripts[@]}"; do
                if [ ! -f "$SCRIPT_DIR/$script" ]; then
                    missing_files+=("$script")
                fi
            done
            
            if [ ${#missing_files[@]} -gt 0 ]; then
                log_error "以下源文件不存在:"
                for file in "${missing_files[@]}"; do
                    log_error "  - $SCRIPT_DIR/$file"
                done
                exit 1
            fi
            
            # 同步每个脚本到服务器（重命名）
            local sync_failed=false
            for i in "${!scripts[@]}"; do
                local source_script="$SCRIPT_DIR/${scripts[$i]}"
                local server_script="$SERVER_BASE_DIR/${server_names[$i]}"
                
                log_info "同步 ${scripts[$i]} -> ${server_names[$i]}..."
                
                local rsync_output
                rsync_output=$(rsync -avz \
                    --exclude='.git/' \
                    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
                    "$source_script" \
                    "$SSH_TARGET:$server_script" \
                    2>&1)
                local rsync_status=$?
                
                # 清理输出
                rsync_output=$(echo "$rsync_output" | grep -v "Warning: Permanently added" | grep -v "sending incremental" | grep -v "sent.*bytes" | grep -v "^$" || true)
                
                if [ $rsync_status -eq 0 ]; then
                    log_success "  ${server_names[$i]} 同步成功"
                else
                    log_error "  ${server_names[$i]} 同步失败"
                    echo "$rsync_output"
                    sync_failed=true
                fi
            done
            
            if [ "$sync_failed" = "true" ]; then
                log_error "部分脚本同步失败"
                exit 1
            fi
            
            log_success "所有服务管理脚本已同步到服务器"
            echo ""
            log_info "使用方法："
            log_info "  1. SSH 到服务器: ssh $SSH_TARGET"
            log_info "  2. 启动服务: bash $SERVER_BASE_DIR/start.sh"
            log_info "  3. 停止服务: bash $SERVER_BASE_DIR/stop.sh"
            log_info "  4. 重启服务: bash $SERVER_BASE_DIR/restart.sh"
            log_info "  5. 检查状态: bash $SERVER_BASE_DIR/status.sh"
            ;;
        all|*)
            sync_directory "$LOCAL_API_DIR" "$SERVER_API_DIR" "API"
            sync_directory "$LOCAL_BACKEND_DIR" "$SERVER_BACKEND_DIR" "Backend"
            sync_directory "$LOCAL_TESTS_DIR" "$SERVER_TESTS_DIR" "Tests"
            if [ -d "$LOCAL_FRONTEND_DIR/dist" ]; then
                sync_directory "$LOCAL_FRONTEND_DIR/dist" "$SERVER_FRONTEND_DIR/dist" "Frontend (dist)"
            fi
            log_success "所有代码同步完成"
            ;;
    esac
    
    echo ""
    log_info "同步完成！"
}

# 运行主函数
main "$@"
