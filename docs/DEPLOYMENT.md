# Deployment Guide

**Version:** 1.0.0  
**Status:** Technical Evaluation  
**Last Updated:** 2025-01-20

## Overview

This guide covers deployment procedures for ExoArmur in technical evaluation environments. For production deployment requirements, see `PRODUCTION_DEPLOYMENT.md`.

## Deployment Modes

### 1. Development Mode

For local development and testing.

**Prerequisites**:
- Python 3.12.3
- Git
- Virtual environment tools

**Steps**:
```bash
# Clone repository
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade "pip>=26.0"
pip install -r requirements.lock
pip install --no-deps -e .

# Verify installation
exoarmur health
```

### 2. Container Mode

For containerized deployment using Docker.

**Prerequisites**:
- Docker 20.10+
- Docker Compose 2.0+

**Steps**:
```bash
# Build container
docker build -t exoarmur-core:latest .

# Run container
docker run -p 8080:8080 exoarmur-core:latest

# Or use Docker Compose
docker-compose up -d

# Verify health
curl http://localhost:8080/health
```

### 3. Kubernetes Mode

For Kubernetes cluster deployment.

**Prerequisites**:
- Kubernetes cluster 1.28+
- kubectl configured
- Helm 3.0+ (optional)

**Steps**:
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Or use Helm
helm install exoarmur ./helm/exoarmur

# Verify deployment
kubectl get pods
kubectl logs -l app=exoarmur

# Port forward for local access
kubectl port-forward svc/exoarmur 8080:8080
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EXOARMUR_ENV` | No | `development` | Environment name |
| `EXOARMUR_LOG_LEVEL` | No | `INFO` | Logging level |
| `EXOARMUR_PORT` | No | `8080` | HTTP port |
| `EXOARMUR_HOST` | No | `0.0.0.0` | Bind address |
| `EXOARMUR_NATS_URL` | Yes* | - | NATS server URL |
| `EXOARMUR_DB_URL` | No | - | PostgreSQL connection string |
| `EXOARMUR_AUDIT_RETENTION_DAYS` | No | `90` | Audit retention period |

*Required if using NATS for event streaming

### Configuration File

Create `/etc/exoarmur/config.yaml`:

```yaml
env: production
log_level: INFO
server:
  port: 8080
  host: 0.0.0.0
nats:
  url: nats://localhost:4222
  jetstream: true
database:
  url: postgresql://user:pass@localhost:5432/exoarmur_audit
audit:
  retention_days: 90
  proof_bundle_path: /var/lib/exoarmur/bundles
```

## Pre-Deployment Checklist

- [ ] Python 3.12.3 installed
- [ ] Dependencies installed from requirements.lock
- [ ] Configuration file created
- [ ] Database schema initialized (if using PostgreSQL)
- [ ] NATS server running (if using NATS)
- [ ] Firewall rules configured
- [ ] Log directories created
- [ ] File permissions set
- [ ] Health check endpoint accessible
- [ ] Monitoring configured

## Post-Deployment Verification

### Health Check

```bash
# Basic health check
exoarmur health

# Expected output:
# ✓ Environment: production
# ✓ Database: connected
# ✓ NATS: connected
# ✓ Audit: enabled
```

### Smoke Tests

```bash
# Run canonical demo
python demos/canonical_truth_reconstruction_demo.py

# Expected output:
# REPLAY_VERDICT=PASS
# CANONICALIZATION_VERSION=v1
# HASH_ALGORITHM=sha256
# HASH=<stable_hash>
```

### Integration Tests

```bash
# Run integration test suite
python -m pytest tests/integration/ -v

# Run specific tests
python -m pytest tests/test_api_integration.py -v
```

## Upgrades

### Upgrade Procedure

```bash
# Stop service
systemctl stop exoarmur

# Backup current version
cp -r /opt/exoarmur /opt/exoarmur.backup.$(date +%Y%m%d)

# Pull latest version
git pull origin main

# Update dependencies
pip install -r requirements.lock
pip install --no-deps -e .

# Run database migrations (if applicable)
python scripts/sql/migrate.py

# Start service
systemctl start exoarmur

# Verify health
exoarmur health
```

### Rollback Procedure

```bash
# Stop service
systemctl stop exoarmur

# Restore previous version
rm -rf /opt/exoarmur
mv /opt/exoarmur.backup.YYYYMMDD /opt/exoarmur

# Start service
systemctl start exoarmur

# Verify health
exoarmur health
```

## Troubleshooting Deployment Issues

### Port Already in Use

**Error**: `Address already in use`

**Solution**:
```bash
# Find process using port
lsof -i :8080

# Kill process or change port
export EXOARMUR_PORT=8081
```

### NATS Connection Failed

**Error**: `NATS connection refused`

**Solution**:
```bash
# Verify NATS is running
nats-server -js

# Check connection string
export EXOARMUR_NATS_URL=nats://localhost:4222
```

### Database Connection Failed

**Error**: `Database connection failed`

**Solution**:
```bash
# Verify PostgreSQL is running
pg_isready

# Check connection string
export EXOARMUR_DB_URL=postgresql://user:pass@localhost:5432/exoarmur_audit

# Test connection
psql $EXOARMUR_DB_URL
```

## Security Considerations

### Secrets Management

Never commit secrets to version control. Use environment variables or secret management systems:

```bash
# Use environment variables
export EXOARMUR_DB_PASSWORD=secure_password

# Or use secret management (Kubernetes)
kubectl create secret generic exoarmur-secrets \
  --from-literal=db-password=secure_password
```

### TLS Configuration

For production-like evaluation, enable TLS:

```yaml
server:
  tls:
    enabled: true
    cert_file: /etc/ssl/certs/exoarmur.crt
    key_file: /etc/ssl/private/exoarmur.key
```

### Network Security

- Restrict access to management endpoints
- Use firewall rules to limit inbound connections
- Implement network segmentation where appropriate

## Performance Considerations

### Resource Allocation

**Minimum Requirements**:
- CPU: 2 cores
- Memory: 4GB
- Disk: 10GB

**Recommended Requirements**:
- CPU: 4 cores
- Memory: 8GB
- Disk: 50GB

### Scaling

For higher throughput:
- Increase worker processes: `export EXOARMUR_WORKERS=4`
- Use connection pooling for database
- Enable NATS clustering for high availability

## Monitoring Integration

### Prometheus

Configure Prometheus scraping:

```yaml
scrape_configs:
  - job_name: 'exoarmur'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
```

### Grafana

Import ExoArmur dashboard from `docs/monitoring/grafana-dashboard.json`

## References

- **Operations Guide**: `docs/OPERATIONS.md`
- **Production Deployment**: `docs/PRODUCTION_DEPLOYMENT.md`
- **Pilot Evaluation**: `docs/PILOT_EVALUATION_GUIDE.md`

---

**Status**: Technical Evaluation - Not for production deployment without security review
