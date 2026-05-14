FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PLAYWRIGHT_BROWSERS_PATH=0
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# By default, run the web server (can be overridden by docker-compose)
CMD ["gunicorn", "--worker-class", "eventlet", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "--preload", "wsgi:app"]
