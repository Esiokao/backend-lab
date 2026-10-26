# frontend/Dockerfile
# 前端正式環境 image：Vite build 產物 + nginx 靜態服務。
# Multi-stage：Node 建置環境不進最終 image（immutable、sha 對應版本）。

FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
