FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY spec/ /app/spec/

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Set Python path
ENV PYTHONPATH=/app/src:/app/scripts

# Default command
CMD ["python3", "scripts/reality_inject.py", "--help"]
