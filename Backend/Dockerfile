# Stage 1: Backend
FROM python:3.10-slim AS backend

# Set working directory for backend
WORKDIR /app/backend

# Copy only the requirements file to leverage Docker caching
COPY Backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir uvicorn

# Copy the entire backend code to the container
COPY . .

# Set environment variable for SQLAlchemy database URL
ENV SQLALCHEMY_DATABASE_URL=mysql+pymysql://user:password@db:3306/database_name

# Expose the backend port (FastAPI)
EXPOSE 7002

# Command to run FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7002"]
