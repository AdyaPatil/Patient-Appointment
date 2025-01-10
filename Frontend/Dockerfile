# Stage 2: Frontend
FROM nginx:latest AS frontend

# Set working directory for nginx
WORKDIR /usr/share/nginx/html

# Remove default Nginx static files
RUN rm -rf ./*

# Copy frontend files
COPY Frontend /usr/share/nginx/html

# Expose the frontend port (Nginx)
EXPOSE 80

# Nginx runs by default, so no need to provide CMD
