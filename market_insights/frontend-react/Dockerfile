# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
# BuildKit npm cache: node_modules cached between rebuilds (first build slow, next ones ~10s)
RUN --mount=type=cache,target=/root/.npm \
    npm ci --cache /root/.npm

ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
