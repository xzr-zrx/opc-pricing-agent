FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && mkdir -p /ms-playwright \
    && python -m playwright install --with-deps chromium \
    && chmod -R 755 /ms-playwright \
    && rm -rf /var/lib/apt/lists/*

COPY app ./app

RUN mkdir -p /app/data/taobao_profile

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]