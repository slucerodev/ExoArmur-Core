# Identity Containment Window (ICW)

## Overview

The Identity Containment Window (ICW) is a **TTL-only, non-permanent** identity containment mechanism for ExoArmur. It provides temporary containment of user identities (sessions, credentials, etc.) with automatic expiration and full audit trails.

## What ICW IS and IS NOT

### ✅ What ICW IS:
- **TTL-only containment**: Temporary containment with enforced time limits
- **Non-permanent**: All containments automatically expire (max 3600 seconds)
- **Audit-tracked**: Complete audit trail for replay and verification
- **Reversible**: Safe automatic reversion when TTL expires
- **Approval-gated**: Requires human approval for containment actions
- **Scope-limited**: Can target specific identity scopes (sessions, credentials, etc.)

### ❌ What ICW IS NOT:
- **NOT permanent identity mutation**: No lasting changes to identity
- **NOT account suspension**: Does not disable or delete accounts
- **NOT privilege escalation**: Does not grant additional permissions
- **NOT persistent blacklisting**: No permanent blocking mechanisms

## TTL Bounds and Configuration

### TTL Limits
- **Maximum TTL**: 3600 seconds (1 hour) - enforced by Pydantic model
- **Effector TTL**: Configurable per-deployment (default: 3600 seconds)
- **Minimum TTL**: 1 second (enforced by validation)

### Supported Scopes
- **SESSIONS**: Contain user sessions
- **CREDENTIALS**: Contain credential access
- **API_KEYS**: Contain API key usage
- **TOKENS**: Contain token access

### Authority Levels
- **A1**: Low-risk containment (5-15 minutes)
- **A2**: Medium-risk containment (15-60 minutes)  
- **A3**: High-risk containment (1-4 hours)
- **A4**: Critical-risk containment (up to 1 hour max)

## Audit Events and Replay

### ICW Audit Events
All ICW operations emit structured audit events:

1. **identity_containment_recommended**
   - Generated when system recommends containment
   - Includes: subject_id, provider, scope, risk_level, ttl_seconds

2. **identity_containment_intent_frozen**
   - Emitted when intent is frozen and bound to approval
   - Includes: intent_id, intent_hash, approval_id, expires_at

3. **identity_containment_applied**
   - Emitted when containment is actually applied
   - Includes: intent_id, subject_id, applied_at, expires_at

4. **identity_containment_reverted**
   - Emitted when containment is reverted (manual or TTL expiry)
   - Includes: intent_id, reason, reverted_at

### Replay Behavior
The ReplayEngine can reconstruct ICW timelines:
- **Deterministic reconstruction**: Same inputs produce same outcomes
- **Reference integrity**: Detects tampered or missing audit events
- **State verification**: Ensures final containment state consistency

## API Endpoints (V2, Feature-Flagged)

### Feature Flag
ICW endpoints are disabled by default. Enable with:
```bash
export ICW_FEATURE_ENABLED=true
```

### Endpoints
- **GET** `/api/v2/identity_containment/status?subject_id=...&provider=...`
  - Get current containment status
  
- **POST** `/api/v2/identity_containment/recommendations`
  - Generate containment recommendations
  
- **POST** `/api/v2/identity_containment/intents/from_recommendation`
  - Freeze intent from recommendation, create approval
  
- **GET** `/api/v2/identity_containment/intents/{intent_id}`
  - Get intent details
  
- **POST** `/api/v2/identity_containment/tick`
  - Process expirations (admin/test only)
  
- **POST** `/api/v2/identity_containment/execute/{approval_id}`
  - Execute containment with approval

## How to Run Demo

### Prerequisites
- Python 3.12+
- ExoArmur dependencies installed
- Feature flag enabled: `ICW_FEATURE_ENABLED=true`

### Demo Script
```bash
# Enable ICW feature flag
export ICW_FEATURE_ENABLED=true

# Run the demo
python3 scripts/demo_identity_containment.py
```

### Demo Flow
1. **Seed observations/beliefs** to trigger recommendation
2. **Generate recommendation** for identity containment
3. **Freeze intent** and create approval request
4. **Approve request** via ApprovalService
5. **Execute containment** apply operation
6. **Advance clock** and process TTL expirations
7. **Show status** before and after revert
8. **Run replay** and verify identical outcomes

## Safety and Security

### Safety Gates
- **Kill Switch**: Global and tenant-level kill switches
- **Policy Verification**: Must pass policy compliance checks
- **Trust Constraints**: Emitter trust score requirements
- **Collective Confidence**: Minimum confidence thresholds

### Approval Requirements
- **Human Approval**: Required for all containment actions
- **Intent Binding**: Approval bound to frozen intent hash
- **Correlation Tracking**: All operations tracked by correlation_id

### Audit Integrity
- **Canonical Hashing**: Intent hashes computed deterministically
- **Event Ordering**: Strict chronological event ordering
- **Reference Validation**: All cross-references verified during replay

## Monitoring and Alerting

### Key Metrics
- **Containment Duration**: Time from apply to revert
- **TTL Compliance**: Percentage of containments respecting TTL limits
- **Approval Latency**: Time from request to approval
- **Replay Success**: Percentage of successful replay reconstructions

### Alert Conditions
- **TTL Exceeded**: Containment exceeding maximum TTL
- **Approval Bypass**: Execution without proper approval
- **Audit Gaps**: Missing audit events in timeline
- **Replay Failures**: Replay reconstruction failures

## Troubleshooting

### Common Issues

**Feature Flag Disabled**
```
Error: "Identity Containment Window feature is not enabled"
Solution: Set ICW_FEATURE_ENABLED=true
```

**TTL Validation Failed**
```
Error: "Input should be greater than 0" or "TTL exceeds maximum"
Solution: Use TTL between 1-3600 seconds
```

**Approval Not Found**
```
Error: "Execution blocked - approval not found or not approved"
Solution: Ensure approval exists and is approved before execution
```

### Debug Commands
```bash
# Check feature flag
echo $ICW_FEATURE_ENABLED

# Verify audit events
curl "http://localhost:8000/v1/audit/{correlation_id}"

# Check containment status
curl "http://localhost:8000/api/v2/identity_containment/status?subject_id=user&provider=okta"
```

## Integration Notes

### NATS Integration
ICW uses NATS JetStream for:
- **Event Publishing**: Audit events and state changes
- **Stream Processing**: Belief aggregation and collective confidence
- **Durable Storage**: Audit record persistence

### Clock Considerations
- **FixedClock**: Used for deterministic testing and replay
- **SystemClock**: Used in production with proper time synchronization
- **TTL Calculations**: All TTL calculations use UTC timestamps

### Multi-tenant Support
- **Tenant Isolation**: Containments isolated by tenant_id
- **Provider Separation**: Different identity providers isolated
- **Scope Limitations**: Containment scopes limited to tenant boundaries
