# syntax=docker/dockerfile:1
# AI 游戏平台 · 前端镜像（构建上下文：apps/frontent-test-1）
#
# Vite 构建产物由 nginx 静态托管（SPA fallback）。
# 前端只使用相对路径（/api/v1、/lg），生产由宿主机 Caddy 同源反代，
# 因此 VITE_* 只需要基路径，不需要任何后端绝对地址。
FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_LG_BASE_URL=/lg
ARG VITE_LG_ASSISTANT_ID=game
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_LG_BASE_URL=${VITE_LG_BASE_URL} \
    VITE_LG_ASSISTANT_ID=${VITE_LG_ASSISTANT_ID}
RUN npm run build

FROM nginx:alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
