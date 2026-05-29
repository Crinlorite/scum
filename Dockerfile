# Multi-stage: build the static site with Node, serve it with nginx.
# Coolify: set Build Pack = "Dockerfile" (port 80).

# ---- build ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# astro build (sin `astro check`: el type-check no debe tumbar un deploy)
RUN npx astro build

# ---- serve ----
FROM nginx:alpine
# Credenciales del panel privado (/panel/). Definir en Coolify como Build Args:
#   PANEL_USER (def. "admin")  y  PANEL_PASS (sin default → panel cerrado si falta).
ARG PANEL_USER=admin
ARG PANEL_PASS=
RUN apk add --no-cache apache2-utils \
    && if [ -n "$PANEL_PASS" ]; then \
         htpasswd -bBc /etc/nginx/.htpasswd "$PANEL_USER" "$PANEL_PASS"; \
       else \
         : > /etc/nginx/.htpasswd; \
       fi
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
