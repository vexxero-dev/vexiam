FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies (build-essential and libffi for crypto/argon2 if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY pyproject.toml .

# Install dependencies and greenlet
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . greenlet

# Copy project source code
COPY . .

# Expose port (Railway dynamically injects $PORT)
EXPOSE ${PORT}

# Run FastAPI app with uvicorn listening on 0.0.0.0 and dynamic $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
