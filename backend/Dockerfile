FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ./backend

# Set Python path so backend module can be imported
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run migrations and start server
WORKDIR /app/backend
CMD ["sh", "-c", "alembic upgrade head && cd /app && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
