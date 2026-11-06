# frontend/Dockerfile
# 前端正式環境 image：Vite build 產物 + nginx 靜態服務。
# Multi-stage：Node 建置環境不進最終 image（immutable、sha 對應版本）。

FROM node:22-alpine AS build

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .

# Turnstile site key（公開值）：build 期由 --build-arg 注入；沒給 = widget 不渲染。
ARG VITE_TURNSTILE_SITE_KEY
ENV VITE_TURNSTILE_SITE_KEY=$VITE_TURNSTILE_SITE_KEY
RUN pnpm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
