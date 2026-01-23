# Audit Event Catalog

This document catalogs all audit events emitted by the ExoArmur system, including their required fields and usage context.

## Overview

Audit events provide a complete, replayable trail of all significant system operations. Each event follows the canonical `AuditEventEnvelope` structure and is emitted through the `AuditService`.

## Event Structure

All audit events use the following envelope structure:

```json
{
    "event_type": "event_type_identifier",
    "timestamp_utc": "2023-12-01T12:00:00Z",
    "correlation_id": "optional_correlation_id",
    "source_federate_id": "source_federate_or_service",
    "event_data": {
        "event_specific_fields": "values"
    }
}
```

## Federation Handshake Events

### handshake_initiated
**Description**: Emitted when a federate initiates a handshake
**Source**: `handshake_controller`
**Required Fields**:
- `handshake_id`: Unique handshake identifier
- `initiator_federate_id`: Federate initiating handshake
- `target_federate_id`: Target federate
- `handshake_version`: Handshake protocol version

**Example**:
```json
{
    "event_type": "handshake_initiated",
    "timestamp_utc": "2023-12-01T12:00:00Z",
    "correlation_id": "hs-123",
    "source_federate_id": "federate-alpha",
    "event_data": {
        "handshake_id": "hs_20231201_120000_abc123",
        "initiator_federate_id": "federate-alpha",
        "target_federate_id": "federate-beta",
        "handshake_version": "2.0.0"
    }
}
```

### handshake_completed
**Description**: Emitted when a handshake successfully completes
**Source**: `handshake_controller`
**Required Fields**:
- `handshake_id`: Handshake identifier
- `final_state`: Final handshake state
- `established_trust_score": Trust score after handshake

**Example**:
```json
{
    "event_type": "handshake_completed",
    "timestamp_utc": "2023-12-01T12:05:00Z",
    "correlation_id": "hs-123",
    "source_federate_id": "federate-alpha",
    "event_data": {
        "handshake_id": "hs_20231201_120000_abc123",
        "final_state": "confirmed",
        "established_trust_score": 0.85
    }
}
```

### handshake_failed
**Description**: Emitted when a handshake fails
**Source**: `handshake_controller`
**Required Fields**:
- `handshake_id`: Handshake identifier
- `failure_reason`: Reason for failure
- `failed_at_step`: Step at which handshake failed

**Example**:
```json
{
    "event_type": "handshake_failed",
    "timestamp_utc": "2023-12-01T12:03:00Z",
    "correlation_id": "hs-123",
    "source_federate_id": "federate-alpha",
    "event_data": {
        "handshake_id": "hs_20231201_120000_abc123",
        "failure_reason": "signature_verification_failed",
        "failed_at_step": "trust_establish"
    }
}
```

### handshake_timeout
**Description**: Emitted when a handshake times out
**Source**: `handshake_controller`
**Required Fields**:
- `handshake_id`: Handshake identifier
- `timeout_duration_seconds`: Timeout duration
- `last_state`: State before timeout

**Example**:
```json
{
    "event_type": "handshake_timeout",
    "timestamp_utc": "2023-12-01T12:10:00Z",
    "correlation_id": "hs-123",
    "source_federate_id": "federate-alpha",
    "event_data": {
        "handshake_id": "hs_20231201_120000_abc123",
        "timeout_duration_seconds": 300,
        "last_state": "identity_exchange"
    }
}
```

## Observation Ingest Events

### observation_ingested
**Description**: Emitted when an observation is successfully ingested
**Source**: `observation_ingest_service`
**Required Fields**:
- `observation_id`: Ingested observation ID
- `source_federate_id`: Federate that sent observation
- `observation_type`: Type of observation
- `confidence`: Observation confidence score

**Example**:
```json
{
    "event_type": "observation_ingested",
    "timestamp_utc": "2023-12-01T12:00:00Z",
    "correlation_id": "obs-456",
    "source_federate_id": "federate-gamma",
    "event_data": {
        "observation_id": "obs_20231201_120000_def456",
        "source_federate_id": "federate-gamma",
        "observation_type": "telemetry_summary",
        "confidence": 0.8
    }
}
```

### observation_rejected
**Description**: Emitted when an observation is rejected
**Source**: `observation_ingest_service`
**Required Fields**:
- `observation_id`: Rejected observation ID
- `source_federate_id`: Federate that sent observation
- `rejection_reason`: Reason for rejection

**Example**:
```json
{
    "event_type": "observation_rejected",
    "timestamp_utc": "2023-12-01T12:00:00Z",
    "correlation_id": "obs-456",
    "source_federate_id": "federate-gamma",
    "event_data": {
        "observation_id": "obs_20231201_120000_def456",
        "source_federate_id": "federate-gamma",
        "rejection_reason": "federate_not_confirmed"
    }
}
```

## Belief Aggregation Events

### belief_created
**Description**: Emitted when a belief is created from observations
**Source**: `belief_aggregation_service`
**Required Fields**:
- `belief_id`: Created belief ID
- `belief_type`: Type of belief
- `confidence`: Belief confidence score
- `source_observations`: Source observation IDs
- `derived_at`: When belief was derived

**Example**:
```json
{
    "event_type": "belief_created",
    "timestamp_utc": "2023-12-01T12:05:00Z",
    "correlation_id": "belief-789",
    "source_federate_id": "belief_aggregation_service",
    "event_data": {
        "belief_id": "belief_20231201_120500_ghi789",
        "belief_type": "derived_from_telemetry_summary",
        "confidence": 0.75,
        "source_observations": ["obs-001", "obs-002"],
        "derived_at": "2023-12-01T12:05:00Z"
    }
}
```

### belief_conflict_detected
**Description**: Emitted when conflicting beliefs are detected
**Source**: `belief_aggregation_service`
**Required Fields**:
- `conflict_key`: Conflict identifier
- `conflicting_beliefs`: List of conflicting belief IDs
- `conflict_type`: Type of conflict detected

**Example**:
```json
{
    "event_type": "belief_conflict_detected",
    "timestamp_utc": "2023-12-01T12:10:00Z",
    "correlation_id": "conflict-999",
    "source_federate_id": "belief_aggregation_service",
    "event_data": {
        "conflict_key": "abc123...",
        "conflicting_beliefs": ["belief-001", "belief-002"],
        "conflict_type": "threat_classification"
    }
}
```

## Arbitration Events

### conflict_detected
**Description**: Emitted when a conflict is detected and arbitration created
**Source**: `conflict_detection_service`
**Required Fields**:
- `arbitration_id`: Created arbitration ID
- `conflict_type`: Type of conflict
- `subject_key`: Subject of conflict
- `conflict_key`: Deterministic conflict key
- `num_claims`: Number of conflicting claims

**Example**:
```json
{
    "event_type": "conflict_detected",
    "timestamp_utc": "2023-12-01T12:15:00Z",
    "correlation_id": "arb-111",
    "source_federate_id": "conflict_detection_service",
    "event_data": {
        "arbitration_id": "arb_20231201_121500_jkl111",
        "conflict_type": "threat_classification",
        "subject_key": "host_A",
        "conflict_key": "abc123...",
        "num_claims": 2
    }
}
```

### arbitration_created
**Description**: Emitted when an arbitration object is created
**Source**: `arbitration_service`
**Required Fields**:
- `arbitration_id`: Arbitration ID
- `conflict_type`: Type of conflict
- `subject_key`: Subject of conflict
- `approval_id`: Approval request ID
- `num_claims`: Number of claims

**Example**:
```json
{
    "event_type": "arbitration_created",
    "timestamp_utc": "2023-12-01T12:15:00Z",
    "correlation_id": "arb-111",
    "source_federate_id": "arbitration_service",
    "event_data": {
        "arbitration_id": "arb_20231201_121500_jkl111",
        "conflict_type": "threat_classification",
        "subject_key": "host_A",
        "approval_id": "approval_arb_20231201_121500_20231201121500",
        "num_claims": 2
    }
}
```

### arbitration_resolution_proposed
**Description**: Emitted when a resolution is proposed for arbitration
**Source**: `arbitration_service`
**Required Fields**:
- `arbitration_id`: Arbitration ID
- `resolution_type`: Type of resolution proposed
- `proposed_by`: Entity proposing resolution

**Example**:
```json
{
    "event_type": "arbitration_resolution_proposed",
    "timestamp_utc": "2023-12-01T12:20:00Z",
    "correlation_id": "arb-111",
    "source_federate_id": "arbitration_service",
    "event_data": {
        "arbitration_id": "arb_20231201_121500_jkl111",
        "resolution_type": "threat_classification_update",
        "proposed_by": "human_operator"
    }
}
```

### arbitration_resolved
**Description**: Emitted when an arbitration is resolved
**Source**: `arbitration_service`
**Required Fields**:
- `arbitration_id`: Arbitration ID
- `resolver_federate_id`: Federate that resolved arbitration
- `resolution_applied_at`: When resolution was applied
- `decision_summary`: Summary of decision

**Example**:
```json
{
    "event_type": "arbitration_resolved",
    "timestamp_utc": "2023-12-01T12:25:00Z",
    "correlation_id": "arb-111",
    "source_federate_id": "resolver-federate",
    "event_data": {
        "arbitration_id": "arb_20231201_121500_jkl111",
        "resolver_federate_id": "resolver-federate",
        "resolution_applied_at": "2023-12-01T12:25:00Z",
        "decision_summary": "Threat classified as trojan"
    }
}
```

### arbitration_rejected
**Description**: Emitted when an arbitration is rejected
**Source**: `arbitration_service`
**Required Fields**:
- `arbitration_id`: Arbitration ID
- `resolver_federate_id`: Federate that rejected arbitration
- `rejection_reason`: Reason for rejection

**Example**:
```json
{
    "event_type": "arbitration_rejected",
    "timestamp_utc": "2023-12-01T12:30:00Z",
    "correlation_id": "arb-111",
    "source_federate_id": "resolver-federate",
    "event_data": {
        "arbitration_id": "arb_20231201_121500_jkl111",
        "resolver_federate_id": "resolver-federate",
        "rejection_reason": "Insufficient evidence"
    }
}
```

## System Events

### feature_flag_changed
**Description**: Emitted when a feature flag is changed
**Source**: `feature_flag_service`
**Required Fields**:
- `flag_name`: Name of feature flag
- `old_value`: Previous flag value
- `new_value`: New flag value
- `changed_by`: Who changed the flag

**Example**:
```json
{
    "event_type": "feature_flag_changed",
    "timestamp_utc": "2023-12-01T12:00:00Z",
    "correlation_id": "flag-123",
    "source_federate_id": "feature_flag_service",
    "event_data": {
        "flag_name": "v2_federation_enabled",
        "old_value": false,
        "new_value": true,
        "changed_by": "system_admin"
    }
}
```

## Event Emission Guidelines

### When to Emit Events
- **Always emit** for state changes (created, updated, deleted)
- **Always emit** for security-relevant operations
- **Always emit** for failures and errors
- **Always emit** for human actions (approvals, rejections)
- **Consider emitting** for significant operations

### Event Data Requirements
- **Required fields** must always be present
- **Optional fields** should be present when relevant
- **Sensitive data** should be omitted or masked
- **Timestamps** must be in UTC with 'Z' suffix
- **IDs** should be stable and deterministic

### Event Ordering
- Events should be emitted in chronological order
- Correlated events should use the same `correlation_id`
- Event timestamps should reflect actual operation time

## Replay Considerations

For replay functionality, audit events must provide:
- **Complete state transitions**: All intermediate states
- **Deterministic identifiers**: Same inputs produce same IDs
- **Causal relationships**: Clear event ordering
- **Human decisions**: Approval/rejection events with reasons

## Event Retention

- **Critical events** (handshakes, arbitrations): 1 year minimum
- **Operational events** (observations, beliefs): 6 months minimum  
- **System events** (feature flags): 1 year minimum
- **Error events**: 3 months minimum

## Monitoring and Alerting

Key events that should trigger monitoring:
- `handshake_failed` - High failure rates
- `observation_rejected` - High rejection rates
- `conflict_detected` - Unusual conflict patterns
- `arbitration_rejected` - High rejection rates
- `feature_flag_changed` - Unauthorized changes
