# Operations Guide

**Version:** 1.0.0  
**Status:** Technical Evaluation  
**Last Updated:** 2025-01-20

## Overview

This guide covers operational procedures for running ExoArmur in a technical evaluation environment. It includes deployment, monitoring, maintenance, and troubleshooting procedures.

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 22.04+ recommended), macOS 13+, or Windows 10+ with WSL2
- **Python**: 3.12.3 (pinned for deterministic behavior)
- **Memory**: 4GB minimum, 8GB recommended
- **Disk**: 10GB free space
- **Network**: Internet access for dependencies

### Software Dependencies

- Docker (for containerized deployment)
- Docker Compose (for multi-container setups)
- NATS Server 2.10+ (for event streaming)
- PostgreSQL 14+ (optional, for audit persistence)

## Deployment

### Development Mode

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

### Containerized Deployment

```bash
# Build container
docker build -t exoarmur-core:latest .

# Run with Docker Compose
docker-compose up -d

# Verify health
curl http://localhost:8080/health
```

### Production-Like Setup

For technical evaluation in a production-like environment:

1. **Environment Configuration**
   ```bash
   export EXOARMUR_ENV=production
   export EXOARMUR_LOG_LEVEL=INFO
   export EXOARMUR_AUDIT_RETENTION_DAYS=90
   ```

2. **Database Setup**
   ```bash
   # PostgreSQL initialization
   createdb exoarmur_audit
   psql exoarmur_audit < scripts/sql/init_schema.sql
   ```

3. **NATS Configuration**
   ```bash
   # Start NATS with JetStream
   nats-server -js -sd /var/lib/nats
   ```

## Monitoring

### Health Checks

```bash
# Basic health check
exoarmur health

# Detailed status
exoarmur proof

# Debug status (development only)
curl http://localhost:8080/v1/debug/status
```

### Metrics

ExoArmur exposes metrics in Prometheus format:

```bash
# Access metrics endpoint
curl http://localhost:8080/metrics
```

Key metrics to monitor:
- `exoarmur_requests_total` - Total request count
- `exoarmur_request_duration_seconds` - Request latency
- `exoarmur_audit_records_total` - Audit record count
- `exoarmur_replay_success_total` - Successful replay count
- `exoarmur_safety_gate_triggered_total` - Safety gate triggers

### Logging

### Log Locations

- **Application Logs**: `/var/log/exoarmur/app.log`
- **Audit Logs**: `/var/log/exoarmur/audit.log`
- **Error Logs**: `/var/log/exoarmur/error.log`

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational information
- **WARNING**: Warning conditions
- **ERROR**: Error conditions
- **CRITICAL**: Critical conditions requiring immediate attention

### Log Rotation

Configure logrotate to manage log file size:

```bash
# /etc/logrotate.d/exoarmur
/var/log/exoarmur/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 exoarmur exoarmur
}
```

## Maintenance

### Updates

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.lock
pip install --no-deps -e .

# Run verification
exoarmur verify-all
```

### Database Maintenance

```bash
# Backup audit database
pg_dump exoarmur_audit > backup_$(date +%Y%m%d).sql

# Vacuum and analyze
psql exoarmur_audit -c "VACUUM ANALYZE;"

# Reindex if needed
psql exoarmur_audit -c "REINDEX DATABASE exoarmur_audit;"
```

### NATS Maintenance

```bash
# Check JetStream status
nats server info

# Stream info
nats stream info AUDIT_STREAM

# Consumer info
nats consumer info AUDIT_STREAM AUDIT_CONSUMER
```

## Troubleshooting

### Common Issues

#### Service Won't Start

**Symptoms**: Service fails to start or crashes immediately

**Diagnosis**:
```bash
# Check logs
journalctl -u exoarmur -n 50

# Check configuration
exoarmur health
```

**Solutions**:
1. Verify Python version is 3.12.3
2. Check port availability (`netstat -tulpn | grep 8080`)
3. Verify NATS connectivity
4. Check file permissions

#### High Memory Usage

**Symptoms**: Memory consumption exceeds expected levels

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep exoarmur
top -p $(pidof exoarmur)
```

**Solutions**:
1. Check for memory leaks in custom plugins
2. Reduce audit retention period
3. Increase system memory
4. Restart service

#### Audit Log Growth

**Symptoms**: Audit logs consuming excessive disk space

**Diagnosis**:
```bash
# Check audit log size
du -sh /var/log/exoarmur/

# Check database size
psql exoarmur_audit -c "SELECT pg_size_pretty(pg_database_size('exoarmur_audit'));"
```

**Solutions**:
1. Configure log rotation
2. Reduce retention period
3. Archive old records
4. Implement partitioning

#### Replay Failures

**Symptoms**: Deterministic replay produces different results

**Diagnosis**:
```bash
# Check replay hash
exoarmur replay --bundle audit_bundle.json

# Verify canonicalization
python -c "from exoarmur.replay.canonical_utils import canonical_json; ..."
```

**Solutions**:
1. Verify schema version compatibility
2. Check for environment differences
3. Validate bundle integrity
4. Check for non-deterministic code

### Debug Mode

Enable debug logging for troubleshooting:

```bash
export EXOARMUR_LOG_LEVEL=DEBUG
exoarmur health
```

### Support Data Collection

When reporting issues, collect:

```bash
# System information
uname -a
python --version
pip list

# ExoArmur information
exoarmur health
exoarmur proof

# Logs
tail -100 /var/log/exoarmur/app.log
tail -100 /var/log/exoarmur/error.log

# Configuration
env | grep EXOARMUR
```

## Backup and Recovery

### Backup Strategy

**Frequency**: Daily backups for audit data

**Retention**: 90 days

**Components**:
1. Audit database
2. Configuration files
3. Proof bundles
4. NATS JetStream data

### Backup Procedure

```bash
#!/bin/bash
# backup_exoarmur.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/exoarmur/$DATE"
mkdir -p "$BACKUP_DIR"

# Database backup
pg_dump exoarmur_audit > "$BACKUP_DIR/audit_db.sql"

# Configuration backup
tar -czf "$BACKUP_DIR/config.tar.gz" /etc/exoarmur/

# Proof bundles backup
tar -czf "$BACKUP_DIR/proof_bundles.tar.gz" /var/lib/exoarmur/bundles/

# NATS JetStream backup
nats stream backup AUDIT_STREAM > "$BACKUP_DIR/nats_stream.json"

# Cleanup old backups
find /backup/exoarmur -mtime +90 -delete
```

### Recovery Procedure

```bash
#!/bin/bash
# restore_exoarmur.sh

BACKUP_DATE=$1
BACKUP_DIR="/backup/exoarmur/$BACKUP_DATE"

# Stop services
systemctl stop exoarmur

# Restore database
psql exoarmur_audit < "$BACKUP_DIR/audit_db.sql"

# Restore configuration
tar -xzf "$BACKUP_DIR/config.tar.gz" -C /

# Restore proof bundles
tar -xzf "$BACKUP_DIR/proof_bundles.tar.gz" -C /

# Restore NATS stream
nats stream restore AUDIT_STREAM < "$BACKUP_DIR/nats_stream.json"

# Start services
systemctl start exoarmur

# Verify
exoarmur health
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_audit_correlation_id ON audit_records(correlation_id);
CREATE INDEX idx_audit_timestamp ON audit_records(created_at);
CREATE INDEX idx_audit_tenant ON audit_records(tenant_id);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM audit_records WHERE correlation_id = '...';
```

### NATS Optimization

```bash
# Configure JetStream for performance
nats stream update AUDIT_STREAM \
  --max-age=72h \
  --max-bytes=1GB \
  --replicas=1 \
  --retention=limits
```

### Application Tuning

```bash
# Environment variables for performance
export EXOARMUR_WORKERS=4
export EXOARMUR_MAX_REQUESTS=1000
export EXOARMUR_REQUEST_TIMEOUT=30
```

## Security

### Access Control

1. **File Permissions**
   ```bash
   # Restrict configuration files
   chmod 600 /etc/exoarmur/config.yaml
   
   # Restrict audit logs
   chmod 640 /var/log/exoarmur/*.log
   ```

2. **Network Security**
   - Use TLS for all network communications
   - Restrict access to management endpoints
   - Implement IP whitelisting where appropriate

3. **Authentication**
   - Enable authentication for NATS
   - Use PostgreSQL authentication
   - Implement API authentication for external access

### Audit Trail

ExoArmur maintains an immutable audit trail of all governance decisions:

```bash
# Query audit records
exoarmur evidence list

# Export specific intent
exoarmur evidence export --intent-id <intent_id>
```

## Scaling

### Horizontal Scaling

For high-throughput scenarios:

1. **Load Balancer**: Deploy multiple instances behind a load balancer
2. **Shared Storage**: Use shared PostgreSQL and NATS cluster
3. **Stateless Design**: Ensure instances are stateless

### Vertical Scaling

For single-instance scenarios:

1. **Increase Resources**: Add CPU and memory
2. **Optimize Database**: Tune PostgreSQL settings
3. **Cache**: Implement caching for frequently accessed data

## Compliance

### Data Retention

Configure retention policies per compliance requirements:

```bash
export EXOARMUR_AUDIT_RETENTION_DAYS=90
export EXOARMUR_PROOF_BUNDLE_RETENTION_DAYS=365
```

### Data Export

Export audit data for compliance reviews:

```bash
# Export all audit records
exoarmur evidence export --all --format json --output audit_export.json

# Export date range
exoarmur evidence export --start-date 2025-01-01 --end-date 2025-01-31
```

### Audit Trail Verification

Regularly verify audit trail integrity:

```bash
# Verify all proof bundles
find /var/lib/exoarmur/bundles -name "*.json" -exec exoarmur verify-bundle --bundle {} \;
```

## References

- **Deployment Guide**: `docs/PRODUCTION_DEPLOYMENT.md`
- **Pilot Evaluation**: `docs/PILOT_EVALUATION_GUIDE.md`
- **Incident Response**: `docs/INCIDENT_RESPONSE.md`
- **Monitoring**: `docs/MONITORING.md`

---

**Status**: Technical Evaluation - Not for production deployment without security review
