# Production Deployment Guide

**Version:** 2.1.0  
**Last Updated:** 2025-01-20  
**Status:** Pilot Ready

## Overview

This guide provides step-by-step instructions for deploying ExoArmur-Core in production environments. It covers infrastructure requirements, configuration, deployment procedures, and operational considerations.

## Prerequisites

### Infrastructure Requirements

#### Minimum Production Specs
- **CPU:** 4 cores (8 recommended for high-throughput)
- **Memory:** 8 GB RAM (16 GB recommended)
- **Storage:** 50 GB SSD (100 GB recommended for audit retention)
- **Network:** Static IP, HTTPS endpoints, firewall capability

#### Required Services
- **NATS Server:** 2.10.x with JetStream enabled
- **PostgreSQL:** 14+ (optional, for persistent audit storage)
- **Load Balancer:** HAProxy, Nginx, or cloud equivalent
- **TLS Certificate:** Valid certificate for HTTPS

### Software Dependencies

#### Container Runtime
- Docker 24.x+ or containerd 1.7+
- Docker Compose 2.20+ (for multi-node deployments)

#### Optional Components
- Kubernetes 1.28+ (for orchestrated deployments)
- Helm 3.13+ (for Helm-based deployments)

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
│              (TLS Termination, Health Checks)           │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼───────┐    ┌───────▼───────┐
│  ExoArmur     │    │  ExoArmur     │
│  Instance 1   │    │  Instance 2   │
│  (Primary)    │    │  (Replica)    │
└───────┬───────┘    └───────┬───────┘
        │                     │
        └──────────┬──────────┘
                   │
         ┌─────────▼─────────┐
         │    NATS Cluster   │
         │  (JetStream KV)   │
         └─────────┬─────────┘
                   │
         ┌─────────▼─────────┐
         │  PostgreSQL       │
         │  (Audit Storage)  │
         └───────────────────┘
```

## Configuration

### Environment Variables

#### Core Configuration
```bash
# Server Configuration
EXOARMUR_HOST=0.0.0.0
EXOARMUR_PORT=8080
EXOARMUR_WORKERS=4

# Feature Flags
EXOARMUR_V2_ENABLED=true
EXOARMUR_DETERMINISM_ENFORCED=true
EXOARMUR_TELEMETRY_ENABLED=true

# NATS Configuration
EXOARMUR_NATS_URLS=nats://nats-1:4222,nats://nats-2:4222,nats://nats-3:4222
EXOARMUR_NATS_STREAM_NAME=EXOARMUR_AUDIT_V1

# Security
EXOARMUR_JWT_SECRET=<generate-strong-secret>
EXOARMUR_API_KEY=<generate-api-key>
```

#### PostgreSQL Audit Store (Optional)
```bash
EXOARMUR_POSTGRES_HOST=postgres.internal
EXOARMUR_POSTGRES_PORT=5432
EXOARMUR_POSTGRES_USER=exoarmur
EXOARMUR_POSTGRES_PASSWORD=<secure-password>
EXOARMUR_POSTGRES_DB=exoarmur_audit
```

### NATS Configuration

#### JetStream Configuration
```hcl
jetstream {
  store_dir: "/data/jetstream"
  max_memory_store: 1GB
  max_file_store: 10GB
}
```

#### KV Buckets
```bash
# Create required KV buckets
nats kv add EXOARMUR_IDEMPOTENCY_V1 --history=1 --ttl=0
nats kv add EXOARMUR_EXECUTION_STATE --history=5
nats kv add EXOARMUR_APPROVAL_STATE --history=10
```

## Deployment Procedures

### Method 1: Docker Compose (Recommended for Single Node)

#### 1. Create Deployment Directory
```bash
mkdir -p /opt/exoarmur/{config,data,certs}
cd /opt/exoarmur
```

#### 2. Create Environment File
```bash
cat > .env << 'EOF'
# Production Environment Configuration
COMPOSE_PROJECT_NAME=exoarmur-prod
EXOARMUR_ENVIRONMENT=production

# Server
EXOARMUR_HOST=0.0.0.0
EXOARMUR_PORT=8080

# Security
EXOARMUR_JWT_SECRET=$(openssl rand -hex 32)
EXOARMUR_API_KEY=$(openssl rand -hex 16)

# NATS
EXOARMUR_NATS_URLS=nats://nats:4222

# Postgres (optional)
EXOARMUR_POSTGRES_HOST=postgres
EXOARMUR_POSTGRES_PORT=5432
EXOARMUR_POSTGRES_USER=exoarmur
EXOARMUR_POSTGRES_PASSWORD=$(openssl rand -hex 16)
EXOARMUR_POSTGRES_DB=exoarmur_audit
EOF
```

#### 3. Deploy
```bash
docker-compose up -d
```

#### 4. Verify Deployment
```bash
# Check health
curl -s https://localhost:8080/health | jq .

# Verify NATS connectivity
docker-compose exec exoarmur-core python -c "
import asyncio
from exoarmur.nats_client import ExoArmurNATSClient
async def check():
    client = ExoArmurNATSClient()
    await client.connect()
    print('NATS connected:', client.is_connected)
    await client.close()
asyncio.run(check())
"
```

### Method 2: Kubernetes (Recommended for Production)

#### 1. Create Namespace
```bash
kubectl create namespace exoarmur
```

#### 2. Apply ConfigMap
```bash
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: exoarmur-config
  namespace: exoarmur
data:
  EXOARMUR_HOST: "0.0.0.0"
  EXOARMUR_PORT: "8080"
  EXOARMUR_WORKERS: "4"
  EXOARMUR_V2_ENABLED: "true"
  EXOARMUR_NATS_URLS: "nats://nats.exoarmur.svc:4222"
EOF
```

#### 3. Apply Secrets
```bash
kubectl apply -f - << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: exoarmur-secrets
  namespace: exoarmur
type: Opaque
stringData:
  EXOARMUR_JWT_SECRET: "$(openssl rand -hex 32)"
  EXOARMUR_API_KEY: "$(openssl rand -hex 16)"
EOF
```

#### 4. Deploy Application
```bash
# Apply deployment
kubectl apply -f k8s/exoarmur-deployment.yaml

# Apply service
kubectl apply -f k8s/exoarmur-service.yaml

# Verify
kubectl get pods -n exoarmur
kubectl logs -n exoarmur -l app=exoarmur-core
```

## Health Checks & Monitoring

### Health Endpoints

#### Liveness Probe
```bash
GET /health

Response 200 OK:
{
  "status": "healthy",
  "component": "exoarmur-core",
  "version": "2.1.0",
  "checks": {
    "nats": "connected",
    "storage": "available"
  }
}
```

#### Readiness Probe
```bash
GET /ready

Response 200 OK when ready to accept traffic
```

### Metrics

ExoArmur exposes Prometheus-compatible metrics at `/metrics`:

```
# HELP exoarmur_audit_records_total Total audit records processed
# TYPE exoarmur_audit_records_total counter
exoarmur_audit_records_total{tenant="acme"} 1543

# HELP exoarmur_execution_duration_seconds Execution duration
# TYPE exoarmur_execution_duration_seconds histogram
exoarmur_execution_duration_seconds_bucket{le="0.1"} 100
```

## Security Considerations

### TLS Configuration

#### Certificate Requirements
- Valid TLS certificate from trusted CA
- Minimum TLS 1.2
- Strong cipher suites

#### Environment Configuration
```bash
EXOARMUR_TLS_CERT=/etc/exoarmur/certs/server.crt
EXOARMUR_TLS_KEY=/etc/exoarmur/certs/server.key
EXOARMUR_TLS_CA=/etc/exoarmur/certs/ca.crt
```

### Network Security

#### Firewall Rules
```bash
# Allow from load balancer only
iptables -A INPUT -p tcp --dport 8080 -s <load-balancer-ip> -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP

# NATS cluster communication
iptables -A INPUT -p tcp --dport 4222 -s <nats-cluster-cidr> -j ACCEPT
```

### Secrets Management

#### Recommended: HashiCorp Vault
```bash
# Configure Vault integration
export EXOARMUR_VAULT_ADDR=https://vault.internal:8200
export EXOARMUR_VAULT_PATH=secret/exoarmur/prod
```

#### Alternative: Kubernetes Secrets
Use sealed-secrets or external-secrets operator for GitOps workflows.

## Backup & Disaster Recovery

### Backup Procedures

#### Audit Records
```bash
# Backup PostgreSQL audit store
pg_dump -h postgres.internal -U exoarmur exoarmur_audit > audit_backup_$(date +%Y%m%d).sql

# Backup NATS JetStream
nats stream backup EXOARMUR_AUDIT_V1 /backup/nats/
```

#### Configuration
```bash
# Backup environment configuration
tar czf config_backup_$(date +%Y%m%d).tar.gz .env docker-compose.yml
```

### Recovery Procedures

#### Full Recovery
1. Restore NATS JetStream from backup
2. Restore PostgreSQL database
3. Redeploy application containers
4. Verify connectivity and data integrity

#### Point-in-Time Recovery
ExoArmur's deterministic replay capability enables reconstruction of system state from any point in the audit trail.

## Troubleshooting

### Common Issues

#### NATS Connection Failures
```bash
# Check NATS connectivity
nats server check connection

# Verify JetStream is enabled
nats server info | grep JetStream
```

#### High Memory Usage
```bash
# Check memory profile
curl -s http://localhost:8080/debug/pprof/heap > heap.prof
go tool pprof heap.prof
```

#### Determinism Violations
```bash
# Check determinism status
curl -s http://localhost:8080/v1/debug/determinism | jq .
```

### Log Analysis

#### Key Log Patterns
```bash
# Search for errors
docker logs exoarmur-core 2>&1 | grep -i error

# Find slow operations
docker logs exoarmur-core 2>&1 | grep "duration_ms.*[0-9]\{4,\}"
```

## Support

### Documentation
- [Configuration Reference](./CONFIGURATION_REFERENCE.md)
- [Operator Runbook](./OPERATOR_RUNBOOK.md)
- [API Documentation](../spec/)

### Emergency Contacts
- On-call rotation: oncall@exoarmur.dev
- Security incidents: security@exoarmur.dev
- General support: support@exoarmur.dev

---

**Document Version:** 2.1.0  
**Review Cycle:** Quarterly  
**Next Review:** 2025-04-20
