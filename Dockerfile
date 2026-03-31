# ExoArmur Deterministic Governance Demo
# Multi-stage build for production-ready container

# Build stage
FROM python:3.12-slim as builder

# Set deterministic environment
ENV PYTHONHASHSEED=0
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash exoarmur

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Production stage
FROM python:3.12-slim as production

# Set deterministic environment
ENV PYTHONHASHSEED=0
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash exoarmur

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY demo_ui.html ./
COPY tests/artifacts/ ./tests/artifacts/

# Set ownership
RUN chown -R exoarmur:exoarmur /app

# Switch to app user
USER exoarmur

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Expose port
EXPOSE 8080

# Metadata
LABEL org.exoarmur.name="ExoArmur Deterministic Governance Demo"
LABEL org.exoarmur.version="1.0.0"
LABEL org.exoarmur.description="Demonstrates deterministic governance capabilities"
LABEL org.exoarmur.determinism="enforced"
LABEL org.exoarmur.python-hash-seed="0"

# Run the demo web server
CMD ["python3", "scripts/demo_web_server.py"]
