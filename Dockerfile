FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    libxrandr2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgdk-pixbuf2.0-0 \
    libxss1 \
    libgconf-2-4 \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir mcp>=1.0.0
RUN pip install --no-cache-dir playwright>=1.40.0
RUN pip install --no-cache-dir fastapi>=0.104.1
RUN pip install --no-cache-dir uvicorn>=0.24.0
RUN pip install --no-cache-dir pydantic>=2.5.0
RUN pip install --no-cache-dir sseclient-py>=0.2.4
RUN pip install --no-cache-dir requests>=2.31.0
RUN pip install --no-cache-dir python-multipart>=0.0.6

RUN playwright install chromium

RUN playwright install-deps chromium

COPY server.py .
COPY server_sse.py .

RUN mkdir -p /app/screenshots

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "server_sse.py"]