# Stage 1: Backend
FROM python:3.10-slim AS backend

# Set working directory for backend
WORKDIR /app/backend

# Copy backend requirements file
COPY Backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn

# Copy backend code
COPY Backend /app/backend

# Stage 2: Frontend
FROM nginx:latest AS frontend

# Set working directory for nginx
WORKDIR /usr/share/nginx/html

# Remove default Nginx static files
RUN rm -rf ./*

# Copy frontend files
COPY Frontend /usr/share/nginx/html

# Stage 3: Final stage combining backend and frontend
FROM python:3.10-slim AS final

# Set working directory for backend
WORKDIR /app/backend

# Copy the backend application from the backend stage
COPY --from=backend /app/backend /app/backend

# Set environment variable for SQLAlchemy database URL
ENV SQLALCHEMY_DATABASE_URL=mysql+pymysql://user:password@db:3306/database_name

# Copy frontend files from the frontend stage
COPY --from=frontend /usr/share/nginx/html /usr/share/nginx/html

# Install Nginx (if you intend to use Nginx directly from this stage)
RUN apt-get update && apt-get install -y nginx

# Expose the backend port (FastAPI)
EXPOSE 7002

# Expose the frontend port (Nginx)
EXPOSE 80

# Command to run FastAPI application and Nginx together
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 7002 & nginx -g 'daemon off;'"]
