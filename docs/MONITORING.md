# Monitoring Guide

**Version:** 1.0.0  
**Status:** Technical Evaluation  
**Last Updated:** 2025-01-20

## Overview

This guide covers monitoring and observability for ExoArmur in technical evaluation environments. It includes metrics collection, alerting, log aggregation, and dashboard configuration.

## Metrics

### Application Metrics

ExoArmur exposes Prometheus-format metrics at `/metrics` endpoint.

#### Key Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `exoarmur_requests_total` | Counter | Total number of requests |
| `exoarmur_request_duration_seconds` | Histogram | Request latency in seconds |
| `exoarmur_audit_records_total` | Counter | Total audit records created |
| `exoarmur_replay_success_total` | Counter | Successful replay operations |
| `exoarmur_replay_failure_total` | Counter | Failed replay operations |
| `exoarmur_safety_gate_triggered_total` | Counter | Safety gate triggers |
| `exoarmur_approval_required_total` | Counter | Approvals required |
| `exoarmur_approval_granted_total` | Counter | Approvals granted |
| `exoarmur_approval_denied_total` | Counter | Approvals denied |

#### System Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `exoarmur_cpu_usage_percent` | Gauge | CPU usage percentage |
| `exoarmur_memory_usage_bytes` | Gauge | Memory usage in bytes |
| `exoarmur_disk_usage_bytes` | Gauge | Disk usage in bytes |
| `exoarmur_nats_connection_status` | Gauge | NATS connection status (0=down, 1=up) |
| `exoarmur_database_connection_status` | Gauge | Database connection status (0=down, 1=up) |

### Prometheus Configuration

Configure Prometheus to scrape ExoArmur metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'exoarmur'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s
```

### Grafana Dashboards

Import the ExoArmur dashboard from `docs/monitoring/grafana-dashboard.json` or create manually:

**Recommended Panels**:

1. **Request Rate**
   - Query: `rate(exoarmur_requests_total[5m])`
   - Type: Graph
   - Description: Requests per second

2. **Request Latency**
   - Query: `histogram_quantile(0.99, rate(exoarmur_request_duration_seconds_bucket[5m]))`
   - Type: Graph
   - Description: P99 latency

3. **Error Rate**
   - Query: `rate(exoarmur_requests_total{status="error"}[5m])`
   - Type: Graph
   - Description: Error rate

4. **Audit Record Rate**
   - Query: `rate(exoarmur_audit_records_total[5m])`
   - Type: Graph
   - Description: Audit records per second

5. **Replay Success Rate**
   - Query: `rate(exoarmur_replay_success_total[5m]) / (rate(exoarmur_replay_success_total[5m]) + rate(exoarmur_replay_failure_total[5m]))`
   - Type: Stat
   - Description: Replay success percentage

6. **Safety Gate Triggers**
   - Query: `rate(exoarmur_safety_gate_triggered_total[5m])`
   - Type: Graph
   - Description: Safety gate triggers per second

7. **System Resources**
   - CPU: `exoarmur_cpu_usage_percent`
   - Memory: `exoarmur_memory_usage_bytes`
   - Disk: `exoarmur_disk_usage_bytes`

## Logging

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational information
- **WARNING**: Warning conditions
- **ERROR**: Error conditions
- **CRITICAL**: Critical conditions

### Log Format

ExoArmur uses structured JSON logging:

```json
{
  "timestamp": "2025-01-20T10:00:00Z",
  "level": "INFO",
  "message": "Request received",
  "correlation_id": "abc123",
  "request_id": "def456",
  "component": "api",
  "tags": {
    "endpoint": "/v1/telemetry/ingest",
    "method": "POST"
  }
}
```

### Log Aggregation

#### ELK Stack (Elasticsearch, Logstash, Kibana)

**Logstash Configuration**:
```conf
input {
  file {
    path => "/var/log/exoarmur/*.log"
    codec => json
  }
}

filter {
  if [level] == "ERROR" or [level] == "CRITICAL" {
    # Alert on errors
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "exoarmur-%{+YYYY.MM.dd}"
  }
}
```

#### Loki + Grafana

**Promtail Configuration**:
```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

scrape_configs:
  - job_name: exoarmur
    static_configs:
      - targets:
          - localhost
        labels:
          job: exoarmur
          __path__: /var/log/exoarmur/*.log
```

### Log Queries

**Common Queries**:

1. **Error Logs**:
   ```
   {level="ERROR"}
   ```

2. **Specific Correlation ID**:
   ```
   {correlation_id="abc123"}
   ```

3. **Time Range**:
   ```
   {level="ERROR"} | timestamp >= "2025-01-20T00:00:00Z" and timestamp <= "2025-01-20T23:59:59Z"
   ```

## Alerting

### Alert Rules

Configure Prometheus alerting rules:

```yaml
# alerting_rules.yml
groups:
  - name: exoarmur_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(exoarmur_requests_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(exoarmur_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P99 latency is {{ $value }} seconds"

      - alert: ReplayFailure
        expr: rate(exoarmur_replay_failure_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Replay failures detected"
          description: "Replay failure rate is {{ $value }} failures/sec"

      - alert: ServiceDown
        expr: up{job="exoarmur"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ExoArmur service is down"
          description: "ExoArmur service has been down for more than 1 minute"

      - alert: HighMemoryUsage
        expr: exoarmur_memory_usage_bytes / exoarmur_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"
```

### Alert Channels

#### PagerDuty

```yaml
# alertmanager.yml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<PAGERDUTY_SERVICE_KEY>'
        description: '{{ .GroupLabels.alertname }}'
```

#### Slack

```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: '<SLACK_WEBHOOK_URL>'
        channel: '#exoarmur-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

#### Email

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'ops-team@organization.com'
        subject: '{{ .GroupLabels.alertname }}'
        body: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

## Health Checks

### HTTP Health Check

```bash
curl http://localhost:8080/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "nats": "connected",
    "database": "connected"
  }
}
```

### Readiness Check

```bash
curl http://localhost:8080/ready
```

**Expected Response**:
```json
{
  "ready": true
}
```

### Liveness Check

```bash
curl http://localhost:8080/live
```

**Expected Response**:
```json
{
  "alive": true
}
```

## Distributed Tracing

### OpenTelemetry Integration

Configure OpenTelemetry for distributed tracing:

```python
# In application startup
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.jaeger import JaegerExporter

# Set up tracing
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Instrument Flask
FlaskInstrumentor().instrument_app(app)
```

### Jaeger UI

Access Jaeger UI at: `http://localhost:16686`

## Performance Monitoring

### APM Tools

#### New Relic

```python
import newrelic.agent

newrelic.agent.initialize(
    license_key='<NEW_RELIC_LICENSE_KEY>',
    app_name='ExoArmur',
    environment='production'
)
```

#### Datadog

```python
from ddtrace import tracer

@tracer.wrap('operation_name')
def some_function():
    # Your code here
    pass
```

### Profiling

Enable profiling for performance analysis:

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

## Synthetic Monitoring

### Uptime Monitoring

Configure uptime monitoring:

```yaml
# uptime.yml
checks:
  - name: ExoArmur Health
    url: http://localhost:8080/health
    interval: 60s
    timeout: 10s
    alert_on:
      - failure
      - response_time_gt: 5s
```

### API Tests

Create synthetic API tests:

```python
# synthetic_tests.py
import requests

def test_health_check():
    response = requests.get('http://localhost:8080/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

def test_metrics_endpoint():
    response = requests.get('http://localhost:8080/metrics')
    assert response.status_code == 200
```

## Monitoring Best Practices

### 1. Golden Signals

Monitor the four golden signals:
- **Latency**: Request processing time
- **Traffic**: Request rate
- **Errors**: Error rate
- **Saturation**: Resource utilization

### 2. Alert Responsibly

- **Alert on symptoms**, not causes
- **Set appropriate thresholds**
- **Avoid alert fatigue**
- **Provide actionable context**

### 3. Use Percentiles

- Use P50, P95, P99 for latency
- Avoid averages (hide outliers)
- Track long-tail behavior

### 4. Monitor Dependencies

- NATS connection status
- Database connection status
- External API health
- Network connectivity

### 5. Log Correlation

- Use correlation IDs
- Include request IDs
- Log at appropriate levels
- Structure logs for querying

## Troubleshooting Monitoring Issues

### Metrics Not Appearing

**Check**:
1. Prometheus is scraping the endpoint
2. Metrics endpoint is accessible
3. Firewall rules allow traffic
4. Service is running

### Alerts Not Firing

**Check**:
1. Alert rules are loaded
2. Alertmanager is configured
3. Notification channels are working
4. Alert conditions are met

### Logs Not Appearing

**Check**:
1. Log aggregation is running
2. Log files exist
3. File permissions are correct
4. Log format is valid

## References

- **Operations Guide**: `docs/OPERATIONS.md`
- **Incident Response**: `docs/INCIDENT_RESPONSE.md`
- **Deployment Guide**: `docs/DEPLOYMENT.md`

---

**Status**: Technical Evaluation - Not for production deployment without security review
