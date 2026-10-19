# syntax=docker/dockerfile:1
# 构建上下文：apps/frontent-test-1
FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# 前端只发相对路径，生产由宿主机 Caddy 同源反代
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_LG_BASE_URL=/lg
ARG VITE_LG_ASSISTANT_ID=game
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_LG_BASE_URL=${VITE_LG_BASE_URL} \
    VITE_LG_ASSISTANT_ID=${VITE_LG_ASSISTANT_ID}
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
