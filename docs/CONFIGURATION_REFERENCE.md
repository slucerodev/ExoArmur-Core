# Configuration Reference

**Version:** 2.1.0  
**Scope:** All ExoArmur-Core configuration options

## Environment Variables

### Core Server Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXOARMUR_HOST` | string | `0.0.0.0` | Server bind address |
| `EXOARMUR_PORT` | integer | `8080` | Server listen port |
| `EXOARMUR_WORKERS` | integer | `4` | Number of worker processes |
| `EXOARMUR_ENVIRONMENT` | string | `development` | Environment label (development, staging, production) |
| `EXOARMUR_LOG_LEVEL` | string | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

### Security Settings

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `EXOARMUR_JWT_SECRET` | string | Yes | Secret key for JWT signing (min 32 bytes) |
| `EXOARMUR_API_KEY` | string | Yes | API key for service-to-service auth |
| `EXOARMUR_TLS_CERT` | path | No | Path to TLS certificate file |
| `EXOARMUR_TLS_KEY` | path | No | Path to TLS private key file |
| `EXOARMUR_TLS_CA` | path | No | Path to CA certificate file |
| `EXOARMUR_ENFORCE_TLS` | boolean | `false` | Require TLS for all connections |

### NATS Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXOARMUR_NATS_URLS` | string | `nats://localhost:4222` | Comma-separated NATS server URLs |
| `EXOARMUR_NATS_STREAM_NAME` | string | `EXOARMUR_AUDIT_V1` | JetStream stream name |
| `EXOARMUR_NATS_KV_PREFIX` | string | `EXOARMUR` | KV bucket prefix |
| `EXOARMUR_NATS_MAX_RECONNECTS` | integer | `10` | Max reconnection attempts |
| `EXOARMUR_NATS_RECONNECT_WAIT` | seconds | `5` | Wait between reconnect attempts |
| `EXOARMUR_NATS_CONNECT_TIMEOUT` | seconds | `10` | Connection timeout |

### PostgreSQL Audit Store

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXOARMUR_POSTGRES_HOST` | string | `localhost` | PostgreSQL host |
| `EXOARMUR_POSTGRES_PORT` | integer | `5432` | PostgreSQL port |
| `EXOARMUR_POSTGRES_USER` | string | `exoarmur` | Database user |
| `EXOARMUR_POSTGRES_PASSWORD` | string | - | Database password |
| `EXOARMUR_POSTGRES_DB` | string | `exoarmur_audit` | Database name |
| `EXOARMUR_POSTGRES_SSL_MODE` | string | `prefer` | SSL mode (disable, prefer, require, verify-ca, verify-full) |
| `EXOARMUR_POSTGRES_POOL_MIN` | integer | `2` | Minimum connection pool size |
| `EXOARMUR_POSTGRES_POOL_MAX` | integer | `10` | Maximum connection pool size |

### Feature Flags

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXOARMUR_V2_ENABLED` | boolean | `true` | Enable V2 governance boundary |
| `EXOARMUR_DETERMINISM_ENFORCED` | boolean | `true` | Enforce deterministic execution |
| `EXOARMUR_TELEMETRY_ENABLED` | boolean | `true` | Enable telemetry collection |
| `EXOARMUR_REPLAY_ENABLED` | boolean | `true` | Enable replay capabilities |
| `EXOARMUR_APPROVAL_REQUIRED` | boolean | `true` | Require human approval for Gate 2+ |

### Circuit Breaker Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXOARMUR_CB_FAILURE_THRESHOLD` | integer | `5` | Failures before opening circuit |
| `EXOARMUR_CB_RECOVERY_TIMEOUT` | seconds | `60` | Wait before half-open |
| `EXOARMUR_CB_SUCCESS_THRESHOLD` | integer | `3` | Successes to close circuit |

### Retry Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXOARMUR_RETRY_MAX_ATTEMPTS` | integer | `3` | Maximum retry attempts |
| `EXOARMUR_RETRY_BASE_DELAY` | seconds | `1.0` | Initial retry delay |
| `EXOARMUR_RETRY_MAX_DELAY` | seconds | `30.0` | Maximum retry delay |
| `EXOARMUR_RETRY_BACKOFF_MULT` | float | `2.0` | Exponential backoff multiplier |
| `EXOARMUR_RETRY_JITTER` | boolean | `true` | Add jitter to retry delays |

### Observability Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EXOARMUR_METRICS_ENABLED` | boolean | `true` | Enable Prometheus metrics |
| `EXOARMUR_METRICS_PORT` | integer | `9090` | Metrics endpoint port |
| `EXOARMUR_TRACING_ENABLED` | boolean | `false` | Enable distributed tracing |
| `EXOARMUR_TRACING_ENDPOINT` | string | - | Tracing collector endpoint |

### Python Environment

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PYTHONHASHSEED` | integer | `0` | Deterministic hash seed |
| `PYTHONUNBUFFERED` | integer | `1` | Unbuffered stdout/stderr |
| `PYTHONDONTWRITEBYTECODE` | integer | `1` | Don't write .pyc files |

## Configuration File Format

### YAML Configuration

ExoArmur supports YAML configuration files for complex deployments:

```yaml
# config/production.yaml
server:
  host: 0.0.0.0
  port: 8080
  workers: 4

security:
  jwt_secret: ${JWT_SECRET}
  api_key: ${API_KEY}
  enforce_tls: true

nats:
  urls:
    - nats://nats-1:4222
    - nats://nats-2:4222
    - nats://nats-3:4222
  stream_name: EXOARMUR_AUDIT_V1
  max_reconnects: 10

postgres:
  host: postgres.internal
  port: 5432
  user: exoarmur
  database: exoarmur_audit
  ssl_mode: require
  pool:
    min: 2
    max: 10

features:
  v2_enabled: true
  determinism_enforced: true
  telemetry_enabled: true
  replay_enabled: true
  approval_required: true

circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 60
  success_threshold: 3

retry:
  max_attempts: 3
  base_delay: 1.0
  max_delay: 30.0
  backoff_multiplier: 2.0
  jitter: true

observability:
  metrics_enabled: true
  metrics_port: 9090
  tracing_enabled: false
```

### Loading Configuration

```python
# From environment variables (default)
from exoarmur.config import load_config
config = load_config()

# From file
config = load_config(path="/etc/exoarmur/config.yaml")

# From specific environment
config = load_config(environment="production")
```

## Configuration Validation

### Built-in Validation

ExoArmur validates configuration on startup:

```python
from exoarmur.config import validate_config

# Validate current configuration
errors = validate_config()
if errors:
    for error in errors:
        print(f"Config error: {error}")
```

### Validation Rules

1. **JWT Secret**: Minimum 32 characters, high entropy
2. **API Key**: Minimum 16 characters
3. **NATS URLs**: Valid URL format, at least one server
4. **PostgreSQL**: Valid connection parameters (if provided)
5. **TLS Files**: Files must exist and be readable
6. **Port Numbers**: Must be valid port ranges (1-65535)

## Environment-Specific Configuration

### Development

```bash
EXOARMUR_ENVIRONMENT=development
EXOARMUR_LOG_LEVEL=DEBUG
EXOARMUR_DETERMINISM_ENFORCED=false
EXOARMUR_TELEMETRY_ENABLED=false
```

### Staging

```bash
EXOARMUR_ENVIRONMENT=staging
EXOARMUR_LOG_LEVEL=INFO
EXOARMUR_ENFORCE_TLS=true
EXOARMUR_APPROVAL_REQUIRED=true
```

### Production

```bash
EXOARMUR_ENVIRONMENT=production
EXOARMUR_LOG_LEVEL=WARNING
EXOARMUR_ENFORCE_TLS=true
EXOARMUR_APPROVAL_REQUIRED=true
EXOARMUR_DETERMINISM_ENFORCED=true
EXOARMUR_METRICS_ENABLED=true
```

## Secrets Management

### Environment Variable Substitution

Configuration files support environment variable substitution:

```yaml
database:
  password: ${EXOARMUR_POSTGRES_PASSWORD}
  # Or with default
  host: ${EXOARMUR_POSTGRES_HOST:localhost}
```

### Vault Integration

For production deployments, ExoArmur supports HashiCorp Vault:

```yaml
vault:
  address: https://vault.internal:8200
  path: secret/exoarmur/prod
  auth_method: kubernetes
```

## Configuration Reload

### Hot Reload

Some configuration changes can be applied without restart:

```bash
# Trigger configuration reload
curl -X POST http://localhost:8080/admin/reload \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

### Reloadable Settings

- Log level
- Feature flags
- Circuit breaker thresholds
- Retry policies
- Metrics configuration

### Non-Reloadable Settings

- Server port and bind address
- NATS connection URLs
- Database connection strings
- TLS certificates

## Troubleshooting Configuration

### Debug Configuration

```bash
# Print effective configuration
exoarmur config --dump

# Validate configuration file
exoarmur config --validate /path/to/config.yaml

# Check specific setting
exoarmur config --get security.jwt_secret
```

### Common Issues

#### Configuration Not Loading
1. Check file permissions
2. Verify YAML syntax
3. Ensure environment variables are exported
4. Check for conflicting settings

#### NATS Connection Failures
1. Verify `EXOARMUR_NATS_URLS` format
2. Check network connectivity
3. Confirm JetStream is enabled
4. Validate authentication credentials

#### PostgreSQL Connection Issues
1. Verify connection string parameters
2. Check SSL mode compatibility
3. Confirm database exists
4. Validate user permissions

---

**Document Version:** 2.1.0  
**Auto-generated:** Partial - manual verification required  
**Last Updated:** 2025-01-20
