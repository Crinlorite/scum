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
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
