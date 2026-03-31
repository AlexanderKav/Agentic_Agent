# docker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    file \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/logs /app/agents/charts /app/data && \
    chmod 755 /app/data

# Copy application code
COPY ./app ./app
COPY ./agents ./agents
COPY ./connectors ./connectors
COPY ./services ./services

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]