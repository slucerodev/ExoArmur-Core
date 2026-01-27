# Feature Flags

This document describes all feature flags in the ExoArmur system, their purposes, default values, and rollout strategies.

## Overview

ExoArmur uses feature flags to control the rollout of V2 functionality while maintaining V1 stability. All V2 features are disabled by default and require explicit enablement.

## Flag Matrix

| Flag Name | Default | Purpose | Dependencies | Risk Level | Owner |
|-----------|---------|---------|--------------|-----------|-------|
| `v2_federation_enabled` | `false` | Enable V2 federation features (handshake, identity) | None | Medium | security_team |
| `v2_observation_ingest_enabled` | `false` | Enable observation ingest and storage | `v2_federation_enabled` | Medium | observability_team |
| `v2_belief_aggregation_enabled` | `false` | Enable belief aggregation from observations | `v2_observation_ingest_enabled` | Low | analytics_team |
| `v2_visibility_api_enabled` | `false` | Enable visibility API endpoints | `v2_belief_aggregation_enabled` | Low | api_team |
| `v2_arbitration_enabled` | `false` | Enable conflict detection and arbitration | `v2_belief_aggregation_enabled` | Medium | security_team |
| `v2_audit_federation_enabled` | `false` | Enable cross-cell audit consolidation | `v2_federation_enabled` | Low | audit_team |
| `v2_advanced_topology_enabled` | `false` | Enable advanced federation topologies | `v2_federation_enabled` | High | networking_team |

## Detailed Flag Descriptions

### v2_federation_enabled
**Description**: Core flag for enabling V2 federation features including handshake protocol, identity management, and federate trust establishment.

**Default**: `false`

**Dependencies**: None

**Features Controlled**:
- HandshakeController operations
- FederateIdentityStore functionality
- Identity exchange and capability negotiation
- Trust establishment and verification

**Rollout Strategy**: Gradual, starting with test federates

**Risk Level**: Medium - Core federation functionality

**Owner**: security_team

**Enablement Checklist**:
- [ ] Certificate infrastructure ready
- [ ] Network connectivity established
- [ ] Security review completed
- [ ] Monitoring in place

### v2_observation_ingest_enabled
**Description**: Enables observation ingest pipeline with signature verification, replay protection, and audit logging.

**Default**: `false`

**Dependencies**: `v2_federation_enabled`

**Features Controlled**:
- ObservationIngestService operations
- Signature verification for observations
- Nonce replay protection
- Observation storage and indexing

**Rollout Strategy**: Gradual, per federate

**Risk Level**: Medium - Data ingestion pipeline

**Owner**: observability_team

**Enablement Checklist**:
- [ ] Storage capacity allocated
- [ ] Signature verification tested
- [ ] Replay protection validated
- [ ] Audit pipeline ready

### v2_belief_aggregation_enabled
**Description**: Enables deterministic belief aggregation from observations with conflict detection.

**Default**: `false`

**Dependencies**: `v2_observation_ingest_enabled`

**Features Controlled**:
- BeliefAggregationService operations
- Deterministic belief generation
- Time-window grouping
- Correlation ID tracking

**Rollout Strategy**: Gradual, per observation type

**Risk Level**: Low - Analytics and aggregation

**Owner**: analytics_team

**Enablement Checklist**:
- [ ] Aggregation rules defined
- [ ] Time-window policies set
- [ ] Performance testing completed
- [ ] Determinism validated

### v2_visibility_api_enabled
**Description**: Enables read-only API endpoints for federation visibility and coordination.

**Default**: `false`

**Dependencies**: `v2_belief_aggregation_enabled`

**Features Controlled**:
- VisibilityAPI endpoints
- Observation and belief listing
- Timeline and correlation views
- Statistics and metrics

**Rollout Strategy**: Gradual, per endpoint

**Risk Level**: Low - Read-only API

**Owner**: api_team

**Enablement Checklist**:
- [ ] API authentication configured
- [ ] Rate limiting in place
- [ ] Documentation updated
- [ ] Client testing completed

### v2_arbitration_enabled
**Description**: Enables conflict detection and human-in-the-loop arbitration for belief conflicts.

**Default**: `false`

**Dependencies**: `v2_belief_aggregation_enabled`

**Features Controlled**:
- ConflictDetectionService operations
- ArbitrationService functionality
- Human approval workflows
- Resolution application

**Rollout Strategy**: Manual, security-controlled

**Risk Level**: Medium - Human decision-making

**Owner**: security_team

**Enablement Checklist**:
- [ ] Approval service integrated
- [ ] Human operators trained
- [ ] Escalation procedures defined
- [ ] Audit trails verified

### v2_audit_federation_enabled
**Description**: Enables cross-cell audit consolidation and federation audit events.

**Default**: `false`

**Dependencies**: `v2_federation_enabled`

**Features Controlled**:
- Cross-cell audit aggregation
- Federation-specific audit events
- Audit replay for federation
- Compliance reporting

**Rollout Strategy**: Gradual, per compliance requirement

**Risk Level**: Low - Audit and compliance

**Owner**: audit_team

**Enablement Checklist**:
- [ ] Audit storage ready
- [ ] Consolidation policies defined
- [ ] Compliance requirements met
- [ ] Retention policies set

### v2_advanced_topology_enabled
**Description**: Enables advanced federation topologies beyond simple peer-to-peer.

**Default**: `false`

**Dependencies**: `v2_federation_enabled`

**Features Controlled**:
- Hierarchical federation
- Hub-spoke topologies
- Multi-region federation
- Dynamic topology changes

**Rollout Strategy**: Manual, network-controlled

**Risk Level**: High - Complex networking

**Owner**: networking_team

**Enablement Checklist**:
- [ ] Network infrastructure ready
- [ ] Topology validation completed
- [ ] Failover procedures tested
- [ ] Performance benchmarks met

## Flag Configuration

### Environment Variables
Flags can be set via environment variables:

```bash
export EXOARMUR_V2_FEDERATION_ENABLED=true
export EXOARMUR_V2_OBSERVATION_INGEST_ENABLED=true
export EXOARMUR_V2_BELIEF_AGGREGATION_ENABLED=true
```

### Configuration File
Flags can be set in configuration files:

```yaml
feature_flags:
  v2_federation_enabled: true
  v2_observation_ingest_enabled: true
  v2_belief_aggregation_enabled: false
  v2_visibility_api_enabled: false
  v2_arbitration_enabled: false
```

### Runtime API
Flags can be changed at runtime via admin API:

```http
POST /api/v1/admin/feature_flags
{
    "flag_name": "v2_federation_enabled",
    "value": true,
    "reason": "Gradual rollout to production federates"
}
```

## Rollout Strategies

### Gradual Rollout
Used for medium-risk flags:
1. Enable for test federates
2. Monitor for 24 hours
3. Enable for 10% of federates
4. Monitor for 48 hours
5. Enable for 50% of federates
6. Monitor for 1 week
7. Enable for all federates

### Manual Rollout
Used for high-risk flags:
1. Security review required
2. Manual approval process
3. Staged enablement per environment
4. Continuous monitoring
5. Rollback procedures ready

### Feature Flag Dependencies
Dependencies are enforced automatically:
- Child flags cannot be enabled if parent is disabled
- Dependencies are validated at startup
- Runtime changes respect dependency rules

## Monitoring and Alerting

### Flag Change Events
All flag changes emit audit events:
```json
{
    "event_type": "feature_flag_changed",
    "timestamp_utc": "2023-12-01T12:00:00Z",
    "source_federate_id": "feature_flag_service",
    "event_data": {
        "flag_name": "v2_federation_enabled",
        "old_value": false,
        "new_value": true,
        "changed_by": "system_admin"
    }
}
```

### Monitoring Metrics
- Flag status per environment
- Feature usage rates
- Error rates by flag
- Performance impact by flag

### Alerting Rules
- Flag changes without approval
- High error rates after flag enablement
- Performance degradation after flag changes
- Dependency violations

## Testing Considerations

### Unit Tests
All feature flags must have unit tests covering:
- Flag disabled behavior (default)
- Flag enabled behavior
- Flag change scenarios
- Dependency validation

### Integration Tests
Feature flag integration tests must verify:
- Cross-service flag coordination
- Dependency enforcement
- Runtime flag changes
- Rollback scenarios

### Canary Testing
High-risk flags should use canary testing:
- Enable for small subset first
- Monitor key metrics
- Automated rollback on issues
- Manual approval for full rollout

## Security Considerations

### Access Control
- Flag changes require authentication
- Authorization based on flag risk level
- Audit trail for all changes
- Emergency disable capability

### Validation
- Flag values validated at runtime
- Invalid values rejected
- Dependency checking enforced
- Rollback safety verified

## Emergency Procedures

### Emergency Disable
Any flag can be disabled immediately:
```bash
# Emergency disable
curl -X POST /api/v1/admin/emergency_flag_disable \
  -H "Authorization: Bearer <token>" \
  -d '{"flag_name": "v2_federation_enabled", "reason": "emergency"}'
```

### Rollback Verification
After emergency disable:
- Verify system stability
- Check V1 functionality
- Monitor error rates
- Validate audit continuity

## Experimental Flag Considerations

### Potential Flags
- `v2_machine_learning_enabled` - ML-based anomaly detection
- `v2_auto_healing_enabled` - Automatic system healing
- `v2_cross_region_sync` - Multi-region synchronization

### Flag Lifecycle
1. **Design**: Define flag purpose and scope
2. **Development**: Implement with proper gating
3. **Testing**: Unit and integration tests
4. **Review**: Security and performance review
5. **Rollout**: Gradual enablement
6. **Monitor**: Continuous observation
7. **Retire**: Remove when feature becomes default

## Best Practices

### Flag Design
- Keep flags simple and boolean when possible
- Use descriptive names with v2 prefix
- Document dependencies clearly
- Define rollback procedures

### Implementation
- Check flags early in service initialization
- Use feature flag wrapper utilities
- Log flag status at startup
- Handle flag changes gracefully

### Operations
- Test flag changes in staging first
- Monitor system health after changes
- Document all flag changes
- Regular flag hygiene reviews
