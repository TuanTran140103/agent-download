# --- Stage 1: Build Stage ---
FROM python:3.12-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Sử dụng uv để cài package siêu nhanh thay cho pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_SYSTEM_PYTHON=1

# Cài đặt nguyên bản từ requirements.txt 
COPY requirements.txt .
RUN uv pip install -r requirements.txt --target /install


# --- Stage 2: Runtime Stage ---
FROM python:3.12-slim

WORKDIR /app

# Copy các thư viện cài đặt ở stage 1 sang thư mục chuẩn của Python
COPY --from=builder /install /usr/local/lib/python3.12/site-packages
COPY --from=builder /install/bin /usr/local/bin

ENV PYTHONUNBUFFERED=1

# Copy toàn bộ mã nguồn (dockerignore sẽ loại trừ file không cần thiết)
COPY . .

# Tạo thư mục dữ liệu nội bộ
RUN mkdir -p /app/downloads /app/logs

EXPOSE 5555

# Chạy ứng dụng
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5555"]
