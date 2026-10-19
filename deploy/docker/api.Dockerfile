# syntax=docker/dockerfile:1
# AI 游戏平台 · api 镜像（构建上下文：apps/api）
#
# 多阶段：builder 用 uv 按 uv.lock 精确安装依赖（含 editable 安装本工程），
#        runtime 只拷贝 .venv 与 app/，以非 root（uid 10001）运行。
# 注意：JWT 私钥/公钥不烘进镜像，运行时从 ./secrets/jwt 挂到 /app/.keys（只读）。
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# 先只装依赖，最大化利用层缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

FROM python:3.14-slim-bookworm AS runtime
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
# uid 固定为 10001：部署侧按这个 uid 授权 JWT 密钥文件（见 deploy/scripts/bootstrap.sh）
RUN groupadd -g 10001 app \
 && useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin app \
 && chown -R 10001:10001 /app
USER 10001:10001
EXPOSE 8000
# --proxy-headers：信任宿主机 Caddy 传来的 X-Forwarded-*
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
