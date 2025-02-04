FROM python:3.10-slim-bookworm

WORKDIR /app

# 配置apt镜像源
RUN rm -rf /etc/apt/sources.list.d/* && \
    rm -f /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-backports main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件并安装
COPY streamlit_app/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 设置环境变量
ARG OPENAI_BASE_URL
ARG OPENAI_API_KEY
ENV OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://dg.bkfeng.top/v1}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# 创建临时目录并设置权限
RUN mkdir -p temp && chmod 777 temp

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 启动应用
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
