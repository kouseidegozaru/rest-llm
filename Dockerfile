# ── ビルドステージ ───────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# 依存パッケージのインストール
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── 本番ステージ ─────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# ビルドステージの依存パッケージをコピー
COPY --from=builder /install /usr/local

# アプリケーションコードをコピー
COPY . .

# 非rootユーザーで実行
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Gunicorn で起動 (開発時は manage.py runserver に差し替え可)
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "180", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
