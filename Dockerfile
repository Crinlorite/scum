# Multi-stage: build the static site with Node, serve it with nginx.
# Coolify: set Build Pack = "Dockerfile" (port 80).

# ---- build ----
FROM node:26-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# astro build (sin `astro check`: el type-check no debe tumbar un deploy)
RUN npx astro build

# ---- serve ----
FROM nginx:alpine
# El panel /panel/ ya NO usa Basic Auth: el acceso lo controla el login con
# Discord (auth_request → backend del host). Solo hace falta curl (healthcheck).
# Las antiguas Build Args PANEL_USER/PANEL_PASS quedan obsoletas (se pueden quitar de Coolify).
RUN apk add --no-cache curl
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# Healthcheck: nginx sirviendo /healthz → Coolify muestra el contenedor "healthy".
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1/healthz || exit 1
EXPOSE 80
