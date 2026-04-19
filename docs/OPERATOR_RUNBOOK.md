# Operator Runbook

**Version:** 2.1.0  
**Audience:** DevOps Engineers, SREs, System Operators  
**Last Updated:** 2025-01-20

## Quick Reference

### Service Status

```bash
# Check overall health
curl -s https://exoarmur.internal/health | jq .

# Check readiness
curl -s https://exoarmur.internal/ready

# Get detailed status
curl -s https://exoarmur.internal/v1/debug/status | jq .
```

### Common Commands

| Command | Purpose |
|---------|---------|
| `docker-compose ps` | List running containers |
| `docker logs -f exoarmur-core` | Tail application logs |
| `nats server check` | Verify NATS cluster health |
| `pg_isready -h postgres` | Check PostgreSQL availability |
| `curl /metrics` | Get Prometheus metrics |

## Incident Response

### Severity Levels

- **P1 (Critical):** Complete service outage, data loss, security breach
- **P2 (High):** Major functionality degraded, potential data impact
- **P3 (Medium):** Partial degradation, workarounds available
- **P4 (Low):** Minor issues, cosmetic problems

### Response Playbook

#### P1 - Service Outage

1. **Assess Impact**
   ```bash
   # Check if service is responding
   curl -s -o /dev/null -w "%{http_code}" https://exoarmur.internal/health
   
   # Check all instances
   for host in exoarmur-{1,2,3}.internal; do
     echo -n "$host: "
     curl -s -o /dev/null -w "%{http_code}" https://$host/health
     echo
   done
   ```

2. **Check Dependencies**
   ```bash
   # Verify NATS
   nats server list
   
   # Verify PostgreSQL
   pg_isready -h postgres.internal -p 5432
   
   # Check load balancer
   curl -s https://lb.internal/stats | jq '.backend_status'
   ```

3. **Restart Procedure**
   ```bash
   # Rolling restart (zero-downtime)
   docker-compose restart exoarmur-core-1
   sleep 30
   docker-compose restart exoarmur-core-2
   sleep 30
   docker-compose restart exoarmur-core-3
   ```

4. **Escalation**
   - Page on-call engineer
   - Notify #incidents channel
   - Update status page
   - Create incident ticket

#### P2 - Degraded Performance

1. **Identify Bottleneck**
   ```bash
   # Check resource usage
   docker stats --no-stream
   
   # Check response times
   curl -s -o /dev/null -w "Time: %{time_total}s\n" https://exoarmur.internal/health
   
   # Review recent errors
   docker logs exoarmur-core --since=1h | grep -i error | tail -20
   ```

2. **Mitigation Options**
   - Scale horizontally: `docker-compose up -d --scale exoarmur-core=5`
   - Increase resource limits
   - Enable circuit breakers
   - Enable rate limiting

3. **Monitor Recovery**
   ```bash
   # Watch error rate
   watch -n 5 'curl -s https://exoarmur.internal/metrics | grep error_rate'
   ```

## Health Checks

### Automated Health Monitoring

```bash
#!/bin/bash
# health_check.sh - Run from cron every minute

HEALTH_URL="https://exoarmur.internal/health"
ALERT_WEBHOOK="https://alerts.internal/webhook"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$response" != "200" ]; then
  curl -X POST $ALERT_WEBHOOK \
    -H "Content-Type: application/json" \
    -d "{\"severity\":\"high\",\"service\":\"exoarmur\",\"status\":\"$response\"}"
fi
```

### Manual Health Check Procedure

1. **HTTP Endpoints**
   ```bash
   # Health check
   curl -s https://exoarmur.internal/health | jq .
   
   # Ready check
   curl -s https://exoarmur.internal/ready
   
   # Debug status
   curl -s https://exoarmur.internal/v1/debug/status | jq .
   ```

2. **Component Status**
   ```bash
   # NATS connectivity
   curl -s https://exoarmur.internal/v1/debug/nats | jq .
   
   # Database connectivity
   curl -s https://exoarmur.internal/v1/debug/database | jq .
   
   # Determinism status
   curl -s https://exoarmur.internal/v1/debug/determinism | jq .
   ```

3. **Metrics Review**
   ```bash
   # Key metrics
   curl -s https://exoarmur.internal/metrics | grep -E "(requests_total|errors_total|duration_seconds)"
   ```

## Maintenance Procedures

### Regular Maintenance

#### Daily
- [ ] Review error logs
- [ ] Check metric dashboards
- [ ] Verify backup completion

#### Weekly
- [ ] Review audit log growth
- [ ] Check certificate expiration
- [ ] Analyze performance trends
- [ ] Rotate logs if needed

#### Monthly
- [ ] Security patch review
- [ ] Capacity planning review
- [ ] Disaster recovery drill
- [ ] Documentation updates

### Deployment Procedures

#### Standard Deployment

1. **Pre-deployment Checks**
   ```bash
   # Verify current health
   curl -s https://exoarmur.internal/health | jq .
   
   # Check git status
   git status
   git log --oneline -5
   
   # Run tests
   pytest tests/ -m "not slow" --tb=short
   ```

2. **Deployment Steps**
   ```bash
   # Pull latest
   git pull origin main
   
   # Build
   docker-compose build exoarmur-core
   
   # Rolling deploy
   docker-compose up -d --no-deps --scale exoarmur-core=2 exoarmur-core
   sleep 30
   docker-compose up -d --no-deps --scale exoarmur-core=1 exoarmur-core
   ```

3. **Post-deployment Verification**
   ```bash
   # Health check
   curl -s https://exoarmur.internal/health | jq .
   
   # Smoke tests
   pytest tests/smoke/ -v
   
   # Monitor for 10 minutes
   watch -n 5 'curl -s https://exoarmur.internal/metrics | grep error_rate'
   ```

### Database Maintenance

#### PostgreSQL Audit Store

1. **Connection Check**
   ```bash
   psql -h postgres.internal -U exoarmur -d exoarmur_audit -c "SELECT COUNT(*) FROM audit_records;"
   ```

2. **Archive Old Records**
   ```bash
   # Run archival
   python scripts/archive_audit_records.py --retention-days=90
   
   # Verify archive
   psql -h postgres.internal -U exoarmur -d exoarmur_audit -c "
     SELECT 
       (SELECT COUNT(*) FROM audit_records) as active,
       (SELECT COUNT(*) FROM audit_records_archive) as archived;
   "
   ```

3. **Vacuum and Analyze**
   ```bash
   psql -h postgres.internal -U exoarmur -d exoarmur_audit -c "VACUUM ANALYZE audit_records;"
   ```

### NATS Maintenance

1. **Stream Status**
   ```bash
   nats stream info EXOARMUR_AUDIT_V1
   ```

2. **Consumer Status**
   ```bash
   nats consumer info EXOARMUR_AUDIT_V1
   ```

3. **Backup**
   ```bash
   nats stream backup EXOARMUR_AUDIT_V1 /backup/nats/$(date +%Y%m%d)
   ```

## Log Analysis

### Log Locations

- **Application:** `docker logs exoarmur-core`
- **System:** `/var/log/exoarmur/`
- **Access:** `/var/log/nginx/exoarmur-access.log`
- **Audit:** Stored in NATS JetStream and PostgreSQL

### Common Log Patterns

#### Error Patterns
```bash
# Find all errors
docker logs exoarmur-core 2>&1 | grep -E "(ERROR|CRITICAL|FATAL)"

# Connection errors
docker logs exoarmur-core 2>&1 | grep "ConnectionError"

# Timeout errors
docker logs exoarmur-core 2>&1 | grep "TimeoutError"
```

#### Performance Patterns
```bash
# Slow requests (> 1s)
docker logs exoarmur-core 2>&1 | grep -E "duration_ms.*[0-9]{4,}"

# High memory usage
docker logs exoarmur-core 2>&1 | grep "Memory usage"
```

### Log Aggregation

#### Configure Fluentd/Fluent Bit
```yaml
[SERVICE]
    Flush 1
    Daemon off

[INPUT]
    Name docker
    Tag exoarmur

[OUTPUT]
    Name es
    Match exoarmur
    Host elasticsearch.internal
    Port 9200
    Index exoarmur-logs
```

## Backup and Recovery

### Backup Procedures

#### Full System Backup
```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR="/backup/exoarmur/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Configuration
tar czf $BACKUP_DIR/config.tar.gz /opt/exoarmur/.env /opt/exoarmur/docker-compose.yml

# NATS
nats stream backup EXOARMUR_AUDIT_V1 $BACKUP_DIR/nats

# PostgreSQL
pg_dump -h postgres.internal -U exoarmur exoarmur_audit > $BACKUP_DIR/audit.sql

# Cleanup old backups (keep 30 days)
find /backup/exoarmur -type d -mtime +30 -exec rm -rf {} \;
```

#### Point-in-Time Recovery

ExoArmur supports deterministic replay for state reconstruction:

```bash
# Reconstruct state at specific time
python scripts/replay_to_timestamp.py \
  --target-time="2025-01-15T10:30:00Z" \
  --output=/tmp/reconstructed_state.json
```

### Recovery Procedures

#### Full System Recovery

1. **Prepare Environment**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com | sh
   
   # Create directories
   mkdir -p /opt/exoarmur/{config,data,certs}
   ```

2. **Restore Configuration**
   ```bash
   cd /opt/exoarmur
   tar xzf /backup/exoarmur/20250120/config.tar.gz
   ```

3. **Restore NATS**
   ```bash
   # Start NATS
   docker-compose up -d nats
   
   # Restore stream
   nats stream restore EXOARMUR_AUDIT_V1 /backup/exoarmur/20250120/nats
   ```

4. **Restore PostgreSQL**
   ```bash
   # Start PostgreSQL
   docker-compose up -d postgres
   
   # Restore database
   psql -h localhost -U exoarmur exoarmur_audit < /backup/exoarmur/20250120/audit.sql
   ```

5. **Start Application**
   ```bash
   docker-compose up -d exoarmur-core
   ```

## Security Operations

### Certificate Management

#### Check Certificate Expiration
```bash
# Check TLS certificate
openssl x509 -in /etc/exoarmur/certs/server.crt -noout -dates

# Check expiration (alert if < 30 days)
openssl x509 -in /etc/exoarmur/certs/server.crt -noout -checkend 2592000 || echo "Certificate expires within 30 days"
```

#### Rotate Certificates
```bash
# Generate new certificate
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes

# Deploy with zero downtime
docker-compose exec -T exoarmur-core sh -c 'cat > /etc/certs/server.crt' < server.crt
docker-compose exec -T exoarmur-core sh -c 'cat > /etc/certs/server.key' < server.key
docker-compose exec exoarmur-core nginx -s reload
```

### Security Monitoring

#### Audit Log Review
```bash
# Check for suspicious activity
psql -h postgres.internal -U exoarmur -d exoarmur_audit -c "
  SELECT tenant_id, event_kind, COUNT(*) 
  FROM audit_records 
  WHERE recorded_at > NOW() - INTERVAL '1 hour'
  GROUP BY tenant_id, event_kind
  ORDER BY COUNT(*) DESC;
"
```

#### Failed Authentication
```bash
# Check for brute force attempts
docker logs exoarmur-core 2>&1 | grep "authentication failed" | awk '{print $4}' | sort | uniq -c | sort -rn
```

## Contact Information

### Escalation Path

1. **Level 1:** On-call Engineer (PagerDuty)
2. **Level 2:** SRE Team Lead
3. **Level 3:** Engineering Manager
4. **Level 4:** CTO (business-critical issues only)

### Support Channels

- **Slack:** #exoarmur-support
- **Email:** oncall@exoarmur.dev
- **Emergency:** +1-XXX-XXX-XXXX (24/7 hotline)
- **Documentation:** https://docs.exoarmur.dev

---

**Document Version:** 2.1.0  
**Next Review:** 2025-04-20  
**Change Log:** See Git history for document changes
