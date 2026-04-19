# Pilot Evaluation Guide

**Version:** 2.1.0  
**Audience:** Design Partners, Evaluation Teams, Solution Architects  
**Last Updated:** 2025-01-20

## Executive Summary

This guide provides a structured framework for evaluating ExoArmur-Core in your environment. It covers success criteria, evaluation scenarios, and measurement methodologies to validate fit for your use case.

## Evaluation Objectives

### Primary Goals

1. **Validate Deterministic Governance**: Confirm all execution paths are governed and auditable
2. **Assess Integration Fit**: Evaluate compatibility with existing infrastructure
3. **Measure Operational Overhead**: Quantify deployment and operational complexity
4. **Verify Safety Guarantees**: Validate safety gate effectiveness for your scenarios

### Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Deployment Time | < 30 minutes | Time from start to first successful request |
| Integration Complexity | Low-Medium | Number of configuration changes required |
| Audit Completeness | 100% | Percentage of execution events captured |
| Replay Accuracy | 100% | Deterministic replay matches original execution |
| Safety Gate Coverage | > 95% | Safety checks triggered when expected |
| Performance Overhead | < 10% | Latency increase vs. baseline |

## Pre-Evaluation Requirements

### Infrastructure Checklist

- [ ] Kubernetes cluster (1.28+) OR Docker Compose environment
- [ ] NATS server (2.10+) with JetStream enabled
- [ ] PostgreSQL (14+) - optional, for audit persistence
- [ ] TLS certificates (for production-like evaluation)
- [ ] Monitoring stack (Prometheus/Grafana recommended)

### Team Requirements

| Role | Time Required | Responsibilities |
|------|---------------|------------------|
| Platform Engineer | 8 hours | Deployment, configuration |
| Security Engineer | 4 hours | Safety policy review, gate validation |
| Developer | 4 hours | API integration, test scenario creation |
| DevOps/SRE | 4 hours | Operational procedures, monitoring |

### Access Requirements

- Container registry access
- Cluster admin rights (for initial deployment)
- Network access between components
- Log/metrics aggregation system access

## Evaluation Scenarios

### Scenario 1: Basic Telemetry Ingestion

**Objective:** Validate end-to-end telemetry processing

**Setup:**
```bash
# Deploy ExoArmur
docker-compose up -d

# Wait for healthy state
curl -s http://localhost:8080/health
```

**Test Procedure:**
```bash
# Send test telemetry
curl -X POST http://localhost:8080/v1/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "1.0.0",
    "event_id": "01J4NR5X9Z8GABCDEF12345678",
    "tenant_id": "pilot-tenant",
    "cell_id": "cell-eval-01",
    "observed_at": "2025-01-20T10:00:00Z",
    "received_at": "2025-01-20T10:00:01Z",
    "source": {
      "kind": "edr",
      "name": "test-edr",
      "host": "test-host-01",
      "sensor_id": "sensor-001"
    },
    "event_type": "process_start",
    "severity": "medium",
    "attributes": {
      "process_name": "test.exe",
      "command_line": "test.exe --param"
    },
    "correlation_id": "pilot-test-001"
  }'
```

**Verification:**
1. HTTP 200 response received
2. Audit record created with matching correlation_id
3. Event appears in NATS JetStream
4. No errors in application logs

### Scenario 2: Safety Gate Evaluation

**Objective:** Validate safety gate triggers appropriately

**Test Cases:**

| Test ID | Gate Level | Trigger Condition | Expected Result |
|---------|------------|-------------------|-----------------|
| SG-001 | A1 | No safety constraints | Execution proceeds |
| SG-002 | A0 | High-confidence scenario | Execution proceeds |
| SG-003 | A0 | Low confidence + reversible | Execution proceeds with monitoring |
| SG-004 | Gate 2 | Low confidence + irreversible | Execution blocked, approval required |
| SG-005 | Gate 2 | Policy violation detected | Execution blocked, approval required |

**Procedure for SG-004 (Approval Required):**
```bash
# 1. Send telemetry that triggers Gate 2
curl -X POST http://localhost:8080/v1/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "1.0.0",
    "event_id": "01J4NR5X9Z8GABCDEF12345679",
    "tenant_id": "pilot-tenant",
    "cell_id": "cell-eval-01",
    "observed_at": "2025-01-20T10:00:00Z",
    "received_at": "2025-01-20T10:00:01Z",
    "source": {"kind": "edr", "name": "test-edr", "host": "test-host-01", "sensor_id": "sensor-001"},
    "event_type": "suspicious_execution",
    "severity": "critical",
    "attributes": {
      "process_name": "malware.exe",
      "command_line": "malware.exe --encrypt",
      "indicators": ["ransomware", "encryption"]
    },
    "correlation_id": "pilot-safety-test-001"
  }'

# 2. Verify execution is pending approval
curl http://localhost:8080/v1/approval/pilot-safety-test-001

# 3. Grant approval
curl -X POST http://localhost:8080/v1/approval/pilot-safety-test-001/approve \
  -H "Content-Type: application/json" \
  -d '{"approver": "security-team", "reason": "Manual review complete"}'

# 4. Verify execution proceeds
```

### Scenario 3: Deterministic Replay

**Objective:** Validate execution replay produces identical results

**Procedure:**
```bash
# 1. Execute scenario and capture correlation ID
CORRELATION_ID="replay-test-$(date +%s)"

# 2. Send telemetry
curl -X POST http://localhost:8080/v1/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d "{\"correlation_id\": \"$CORRELATION_ID\", ...}"

# 3. Capture original execution result
ORIGINAL=$(curl -s http://localhost:8080/v1/audit/$CORRELATION_ID)

# 4. Execute replay
REPLAY=$(curl -X POST http://localhost:8080/v1/replay \
  -H "Content-Type: application/json" \
  -d "{\"correlation_id\": \"$CORRELATION_ID\"}")

# 5. Compare results
# Results should be byte-identical (excluding timestamps)
```

### Scenario 4: Byzantine Fault Tolerance

**Objective:** Validate system behavior under adversarial conditions

**Procedure:**
```bash
# Run Byzantine fault injection test
curl -X POST http://localhost:8080/v1/test/byzantine \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "partial",
    "fault_ratio": 0.33,
    "correlation_id": "byzantine-test-001"
  }'

# Expected: System detects and reports divergence
# Consensus reached on correct execution path
```

### Scenario 5: Load Testing

**Objective:** Measure performance under representative load

**Tools:**
- k6 or Apache Bench for HTTP load testing
- NATS monitoring for message throughput

**Test Parameters:**
| Metric | Target | Duration |
|--------|--------|----------|
| Requests/second | 100 | 5 minutes |
| Concurrent connections | 10 | 5 minutes |
| Latency (p99) | < 500ms | 5 minutes |
| Error rate | < 0.1% | 5 minutes |

## Evaluation Metrics

### Quantitative Metrics

#### Performance
```bash
# Measure response time
curl -s -o /dev/null -w "Connect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" \
  http://localhost:8080/health

# Load test with k6
cat > load_test.js << 'EOF'
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 10,
  duration: '5m',
};

export default function () {
  const res = http.get('http://localhost:8080/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
}
EOF
k6 run load_test.js
```

#### Reliability
- Uptime percentage
- Mean time between failures (MTBF)
- Mean time to recovery (MTTR)
- Error rate by category

#### Resource Utilization
- CPU usage
- Memory consumption
- Network I/O
- Storage growth rate

### Qualitative Assessment

#### Operational Complexity

| Aspect | Rating (1-5) | Notes |
|--------|--------------|-------|
| Deployment ease | | |
| Configuration clarity | | |
| Documentation quality | | |
| Error message clarity | | |
| Upgrade process | | |
| Monitoring integration | | |

#### Security Assessment

- Safety gate coverage for your use cases
- Audit completeness
- Replay accuracy
- Policy enforcement effectiveness

## Evaluation Timeline

### Week 1: Setup & Baseline

| Day | Activities | Deliverables |
|-----|------------|--------------|
| 1 | Infrastructure setup, deployment | Running ExoArmur instance |
| 2 | Basic integration, health checks | Integration test results |
| 3 | Scenario 1 & 2 execution | Telemetry and safety validation |
| 4 | Performance baseline measurement | Performance metrics document |
| 5 | Issue documentation, vendor sync | Issue tracker, feedback report |

### Week 2: Deep Evaluation

| Day | Activities | Deliverables |
|-----|------------|--------------|
| 6 | Scenario 3 (replay) validation | Replay accuracy report |
| 7 | Scenario 4 (Byzantine) testing | Fault tolerance report |
| 8 | Load testing, stress scenarios | Load test results |
| 9 | Operational procedure testing | Runbook validation |
| 10 | Documentation review | Gap analysis |

### Week 3: Analysis & Reporting

| Day | Activities | Deliverables |
|-----|------------|--------------|
| 11 | Data analysis, metric compilation | Evaluation metrics summary |
| 12 | Report writing | Draft evaluation report |
| 13 | Stakeholder review | Review feedback |
| 14 | Final report, go/no-go recommendation | Final evaluation report |

## Evaluation Report Template

### Executive Summary

- Overall fit rating (1-5)
- Go/No-go recommendation
- Key findings summary
- Critical blockers (if any)

### Technical Assessment

#### Deployment Experience
- Time to deploy: ___ minutes
- Configuration complexity: Low/Medium/High
- Integration issues encountered: ___
- Documentation gaps: ___

#### Functionality Validation

| Feature | Status | Notes |
|---------|--------|-------|
| Telemetry ingestion | Pass/Fail | |
| Safety gate triggering | Pass/Fail | |
| Approval workflow | Pass/Fail | |
| Audit logging | Pass/Fail | |
| Replay capability | Pass/Fail | |
| Byzantine resilience | Pass/Fail | |

#### Performance Results

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Response time (p50) | < 100ms | ___ms | |
| Response time (p99) | < 500ms | ___ms | |
| Throughput | > 100 req/s | ___req/s | |
| Error rate | < 0.1% | ___% | |
| CPU usage | < 50% | ___% | |
| Memory usage | < 1GB | ___GB | |

### Operational Assessment

#### Monitoring & Observability
- Metrics coverage: ___
- Alert effectiveness: ___
- Log quality: ___
- Dashboard utility: ___

#### Operational Procedures
- Deployment complexity: ___
- Upgrade process: ___
- Backup/restore: ___
- Troubleshooting guide utility: ___

### Business Assessment

#### Value Proposition
- Problem fit: ___
- ROI potential: ___
- Competitive differentiation: ___

#### Risk Assessment
- Technical risks: ___
- Operational risks: ___
- Vendor risks: ___

### Recommendations

#### Immediate Actions
1. ___
2. ___
3. ___

#### Long-term Considerations
1. ___
2. ___
3. ___

## Feedback Channels

### During Evaluation

- **Slack:** #exoarmur-pilot-support
- **Email:** pilot-support@exoarmur.dev
- **Office Hours:** Tuesdays/Thursdays 2-3 PM ET

### Post-Evaluation

- **Feedback Form:** https://exoarmur.dev/pilot-feedback
- **Feature Requests:** https://github.com/exoarmur/core/issues
- **Security Issues:** security@exoarmur.dev

## Appendix

### A. Quick Reference Card

```
Health Check:  curl http://localhost:8080/health
Metrics:       curl http://localhost:8080/metrics
Debug Status:  curl http://localhost:8080/v1/debug/status
Logs:          docker logs -f exoarmur-core
Restart:       docker-compose restart exoarmur-core
```

### B. Common Issues

| Issue | Solution |
|-------|----------|
| NATS connection refused | Verify NATS is running and accessible |
| Port already in use | Change EXOARMUR_PORT or stop conflicting service |
| Permission denied | Check file permissions on mounted volumes |
| TLS handshake failed | Verify certificate validity and configuration |

### C. Support Resources

- Documentation: https://docs.exoarmur.dev
- API Reference: https://api.exoarmur.dev
- Community: https://community.exoarmur.dev
- Status Page: https://status.exoarmur.dev

---

**Document Version:** 2.1.0  
**Evaluation Period:** 2-3 weeks recommended  
**Questions?** Contact pilot-support@exoarmur.dev
