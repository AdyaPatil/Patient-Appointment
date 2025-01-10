# Stage 1: Backend
FROM python:3.10-slim AS backend

# Set working directory
WORKDIR /app/backend

# Copy backend requirements
COPY Backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Backend directory to the container
COPY Backend /app/backend

# Stage 2: Frontend
FROM nginx:latest AS frontend

# Set working directory for nginx
WORKDIR /usr/share/nginx/html

# Remove default Nginx static files
RUN rm -rf ./*

# Copy frontend files
COPY Frontend /usr/share/nginx/html

# Stage 3: Final stage combining backend and database
FROM backend AS final

# Expose backend port
EXPOSE 8000

# Set environment variable for SQLAlchemy database URL
ENV SQLALCHEMY_DATABASE_URL=mysql+pymysql://user:password@db:3306/database_name

# Command to run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
