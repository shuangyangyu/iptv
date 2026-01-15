# Home Assistant Addon Dockerfile
# 基于 Dockerfile.backend，适配 HA addon 环境
# HA addon 使用 BUILD_FROM 参数指定基础镜像

ARG BUILD_FROM
FROM ${BUILD_FROM}

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# 注意：HA addon 基础镜像通常是 Alpine，使用 apk
RUN \
    apk add --no-cache --virtual .build-deps \
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
    || ( \
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
            python3-pip \
    )

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
RUN which udpxy || (echo "WARNING: udpxy not found, will try to compile from source" && false) || true

# 如果 udpxy 仍未安装，再次尝试编译
RUN \
    if ! command -v udpxy > /dev/null 2>&1; then \
        echo "Compiling udpxy from source..." && \
        cd /tmp && \
        git clone --depth 1 https://github.com/pcherenkov/udpxy.git && \
        cd udpxy/chipmunk && \
        make && \
        make install && \
        rm -rf /tmp/udpxy && \
        which udpxy || (echo "ERROR: Failed to install udpxy" && exit 1); \
    fi

# 创建 iptv_sever 目录结构
RUN mkdir -p /app/iptv_sever

# 复制 Python 依赖文件
# 注意：HA addon 构建时，构建上下文是仓库根目录
# Dockerfile 在 addon 目录中，但 COPY 路径相对于仓库根目录
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
# 构建上下文是仓库根目录，所以路径是 addon/run.sh
COPY addon/run.sh /run.sh
RUN chmod a+x /run.sh

# 暴露端口
EXPOSE 8088 4022

# 启动命令
CMD ["/run.sh"]
