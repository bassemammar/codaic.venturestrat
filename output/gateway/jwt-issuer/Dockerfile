FROM python:3.11-slim

LABEL maintainer="VentureStrat Team"
LABEL description="JWT Issuer service for VentureStrat Gateway"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create non-root user for security
RUN groupadd -r jwt-issuer && useradd -r -g jwt-issuer jwt-issuer
RUN chown -R jwt-issuer:jwt-issuer /app
USER jwt-issuer

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
