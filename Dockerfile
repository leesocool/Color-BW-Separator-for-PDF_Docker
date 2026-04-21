FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制服务代码和前端静态文件
COPY serverless_handler/ ./serverless_handler/

# 创建数据目录（挂载卷时会被覆盖）
RUN mkdir -p /data/input /data/output

EXPOSE 9000

CMD ["python", "serverless_handler/ws_server.py"]
