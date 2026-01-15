# Home Assistant Addon Dockerfile
# 基于 Dockerfile.backend，适配 HA addon 环境
# HA addon 使用 BUILD_FROM 参数指定基础镜像

ARG BUILD_FROM
FROM ${BUILD_FROM}

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# HA addon 基础镜像通常是 Alpine
RUN apk add --no-cache \
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
    dcron \
    || true

# 如果包管理器没有 udpxy，从源码编译
RUN \
    if ! command -v udpxy > /dev/null 2>&1; then \
        echo "Installing udpxy from source..." && \
        cd /tmp && \
        git clone --depth 1 https://github.com/pcherenkov/udpxy.git && \
        cd udpxy/chipmunk && \
        make && \
        make install && \
        rm -rf /tmp/udpxy; \
    fi

# 验证 udpxy 安装（如果失败，允许继续，运行时再处理）
RUN which udpxy || echo "WARNING: udpxy not found, will try to install at runtime"

# 创建 iptv_sever 目录结构
RUN mkdir -p /app/iptv_sever/api /app/iptv_sever/backend /app/iptv_sever/out

# 从 GitHub 克隆项目代码（因为构建上下文可能无法访问父目录）
# 使用 --depth=1 只克隆最新代码，节省空间和时间
RUN cd /tmp && \
    git clone --depth=1 https://github.com/shuangyangyu/iptv.git iptv-repo && \
    cp -r iptv-repo/iptv_sever/api /app/iptv_sever/ && \
    cp -r iptv-repo/iptv_sever/backend /app/iptv_sever/ && \
    rm -rf iptv-repo

# 安装 Python 依赖
RUN pip3 install --no-cache-dir -r /app/iptv_sever/api/requirements.txt || \
    pip install --no-cache-dir -r /app/iptv_sever/api/requirements.txt

# 创建 __init__.py 文件
RUN touch /app/iptv_sever/__init__.py

# 设置 PYTHONPATH
ENV PYTHONPATH=/app

# 复制启动脚本
# 构建上下文是 addon 目录，所以直接复制 run.sh
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# 暴露端口
EXPOSE 8088 4022

# 启动命令
CMD ["/run.sh"]
