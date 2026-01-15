# Home Assistant Addon Dockerfile
# 基于 Dockerfile.backend，适配 HA addon 环境
# HA addon 使用 BUILD_FROM 参数指定基础镜像

ARG BUILD_FROM
FROM ${BUILD_FROM}

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# 注意：HA addon 基础镜像可能是 Alpine 或 Debian，需要兼容两种包管理器
RUN \
    if [ -f /etc/alpine-release ]; then \
        # Alpine Linux
        apk add --no-cache \
            curl \
            wget \
            lsof \
            net-tools \
            iproute2 \
            git \
            make \
            gcc \
            musl-dev \
            linux-headers \
            python3-dev \
            py3-pip \
            || true; \
    else \
        # Debian/Ubuntu
        apt-get update && \
        apt-get install -y --no-install-recommends \
            curl \
            wget \
            lsof \
            net-tools \
            iproute2 \
            git \
            make \
            gcc \
            build-essential \
            python3-dev \
            || true; \
    fi

# 如果包管理器没有 udpxy，从源码编译
RUN \
    if ! command -v udpxy > /dev/null 2>&1; then \
        cd /tmp && \
        git clone https://github.com/pcherenkov/udpxy.git && \
        cd udpxy/chipmunk && \
        make && \
        make install && \
        rm -rf /tmp/udpxy; \
    fi

# 验证 udpxy 安装
RUN which udpxy || (echo "ERROR: udpxy not found" && exit 1)

# 创建 iptv_sever 目录结构
RUN mkdir -p /app/iptv_sever

# 复制 Python 依赖文件
COPY iptv_sever/api/requirements.txt /app/iptv_sever/api/requirements.txt

# 安装 Python 依赖
# 兼容 pip 和 pip3
RUN \
    if command -v pip3 > /dev/null; then \
        pip3 install --no-cache-dir -r /app/iptv_sever/api/requirements.txt; \
    else \
        pip install --no-cache-dir -r /app/iptv_sever/api/requirements.txt; \
    fi

# 复制项目代码
COPY iptv_sever/api /app/iptv_sever/api
COPY iptv_sever/backend /app/iptv_sever/backend

# 创建 __init__.py 文件（如果不存在）
RUN touch /app/iptv_sever/__init__.py 2>/dev/null || true

# 设置 PYTHONPATH
ENV PYTHONPATH=/app

# 创建必要的目录
RUN mkdir -p /app/iptv_sever/out /app/iptv_sever/api

# 复制启动脚本
COPY addon/run.sh /run.sh
RUN chmod a+x /run.sh

# 暴露端口
EXPOSE 8088 4022

# 启动命令
CMD ["/run.sh"]
