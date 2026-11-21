# Stage 1: Builder
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies cleanly from lockfile
COPY package*.json ./
RUN npm ci

# Accept build arguments for environment variables (defaults to same-origin reverse proxy)
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Copy source code and build the Vite/React app
COPY . .
RUN npm run build


# Stage 2: Production Server (Unprivileged Nginx)
FROM nginxinc/nginx-unprivileged:alpine

# Copy build files from the Builder stage (Vite outputs to /dist)
COPY --chown=nginx:nginx --from=builder /app/dist /usr/share/nginx/html

# Copy our custom Nginx routing config
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]