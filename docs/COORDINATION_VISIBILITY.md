# Coordination Visibility - Observation and Belief System

## Overview

The Coordination Visibility system provides a read-only observation and belief aggregation capability for ExoArmur V2. This system allows federates to share observations about their environment and automatically derive beliefs through deterministic aggregation.

## Architecture

### Core Components

1. **Observation Schemas** - Typed Pydantic models for observation messages
2. **Observation Store** - Deterministic storage with provenance tracking
3. **Observation Ingest Service** - Validation, verification, and ingestion pipeline
4. **Belief Aggregation Service** - Deterministic aggregation of observations into beliefs
5. **Visibility API** - Read-only endpoints for querying observations and beliefs

### Key Principles

- **V1 Unchanged**: All existing V1 functionality preserved
- **V2 Additive Only**: New features are additive and default to OFF
- **Observation Only**: No actions, automation, or posture changes
- **Deterministic**: Same inputs always produce same beliefs
- **Provenance Tracking**: Full audit trail and correlation links
- **Security First**: Only confirmed federates can submit observations

## Observation Schemas

### Base Observation Model

```python
class ObservationV1(BaseModel):
    """Canonical observation message from a federate"""
    schema_version: str = "2.0.0"
    observation_id: str
    source_federate_id: str
    timestamp_utc: datetime
    correlation_id: Optional[str]
    nonce: Optional[str]  # For replay protection
    observation_type: ObservationType
    confidence: float  # 0.0 to 1.0
    evidence_refs: List[str]
    payload: ObservationPayloadV1
    signature: Optional[SignatureInfoV1]
```

### Observation Types

1. **TELEMETRY_SUMMARY** - Summarized telemetry events
2. **THREAT_INTEL** - Threat intelligence indicators
3. **ANOMALY_DETECTION** - Detected anomalies
4. **SYSTEM_HEALTH** - System health metrics
5. **NETWORK_ACTIVITY** - Network activity summaries
6. **CUSTOM** - Custom observation types

### Payload Models

Each observation type has a specific payload model with typed fields:

```python
# Example: Telemetry Summary
class TelemetrySummaryPayloadV1(ObservationPayloadV1):
    event_count: int
    time_window_seconds: int
    event_types: List[str]
    severity_distribution: Dict[str, int]

# Example: Threat Intelligence
class ThreatIntelPayloadV1(ObservationPayloadV1):
    ioc_count: int
    threat_types: List[str]
    confidence_score: float
    sources: List[str]
```

## Observation Ingest Pipeline

### Validation Steps

1. **Feature Flag Check** - V2 feature must be enabled
2. **Federate Validation** - Federate must exist and be confirmed
3. **Schema Validation** - Observation must pass schema validation
4. **Signature Verification** - Signature must be valid (if required)
5. **Replay Protection** - Nonce must not have been used
6. **Duplicate Check** - Observation ID must be unique

### Security Requirements

- **Confirmed Federates Only**: Only federates with successful handshakes can submit
- **Mandatory Signatures**: All observations must be cryptographically signed
- **Replay Protection**: Nonces prevent replay attacks
- **Schema Validation**: Strict validation prevents malformed data

### Audit Events

Every ingest operation emits audit events:

```python
{
    "event_type": "observation_accepted" | "observation_rejected",
    "federate_id": "source-federate",
    "observation_id": "obs-123",
    "correlation_id": "corr-456",
    "observation_type": "telemetry_summary",
    "timestamp": "2023-01-01T12:00:00Z",
    "reason": "success" | "failure_reason",
    "details": {
        "confidence": 0.8,
        "payload_type": "telemetry_summary",
        "evidence_refs": ["evidence-1"]
    }
}
```

## Belief Aggregation

### Deterministic Grouping

Observations are grouped by:
- Observation type
- Correlation ID
- Time window (hourly)
- Payload-specific attributes

### Aggregation Rules

Each observation type has specific aggregation rules:

#### Telemetry Summary
- Sum event counts
- Average confidence
- Combine severity distributions

#### Threat Intelligence
- Sum IOC counts
- Combine threat types
- Average confidence scores
- Merge sources

#### Anomaly Detection
- Average anomaly scores
- Combine affected entities
- Average baseline deviations

#### System Health
- Average utilization metrics
- Calculate health score
- Combine service status

#### Network Activity
- Sum connections and bytes
- Combine protocols
- Count suspicious IPs

### Belief Model

```python
class BeliefV1(BaseModel):
    """Canonical belief derived from observations"""
    schema_version: str = "2.0.0"
    belief_id: str
    belief_type: str
    confidence: float
    source_observations: List[str]  # Provenance
    derived_at: datetime
    correlation_id: Optional[str]
    evidence_summary: str
    conflicts: List[str]  # No auto-resolution
    metadata: Dict[str, Any]
```

### Conflict Handling

- **No Auto-Resolution**: Conflicts are marked but not automatically resolved
- **Manual Arbitration**: Conflicts require manual review and arbitration
- **Provenance Retained**: All source observations preserved for replay

## Visibility API

### Endpoints

#### List Federates
```
GET /api/v2/visibility/federates
```
Returns all federates with their status and roles.

#### List Observations
```
GET /api/v2/visibility/observations
```
Filters:
- `federate_id` - Filter by source federate
- `correlation_id` - Filter by correlation ID
- `observation_type` - Filter by observation type
- `since` - Filter by timestamp (ISO format)
- `limit` - Maximum results to return

#### List Beliefs
```
GET /api/v2/visibility/beliefs
```
Filters:
- `correlation_id` - Filter by correlation ID
- `belief_type` - Filter by belief type
- `since` - Filter by timestamp (ISO format)
- `limit` - Maximum results to return

#### Get Timeline
```
GET /api/v2/visibility/timeline/{correlation_id}
```
Returns all observations and beliefs for a correlation ID in chronological order.

#### Get Statistics
```
GET /api/v2/visibility/statistics
```
Returns system statistics and configuration.

### Response Models

All responses include provenance information:

```python
{
    "observation_id": "obs-123",
    "source_federate_id": "federate-1",
    "timestamp_utc": "2023-01-01T12:00:00Z",
    "correlation_id": "corr-456",
    "observation_type": "telemetry_summary",
    "confidence": 0.8,
    "evidence_refs": ["evidence-1"],
    "payload_type": "telemetry_summary",
    "payload_data": {...}
}
```

## Configuration

### Feature Flags

```python
# Observation Ingest Configuration
class ObservationIngestConfig:
    feature_enabled: bool = False  # V2 additive feature
    require_confirmed_federate: bool = True
    require_signature: bool = True
    max_observation_size_bytes: int = 1024 * 1024

# Belief Aggregation Configuration
class BeliefAggregationConfig:
    feature_enabled: bool = False  # V2 additive feature
    min_observations_for_belief: int = 1
    confidence_threshold: float = 0.5
    max_beliefs_per_type: int = 100
    aggregation_window_minutes: int = 60
```

### Store Configuration

```python
class ObservationStoreConfig:
    max_observations_per_federate: int = 10000
    max_beliefs: int = 5000
    observation_ttl_hours: int = 72
    belief_ttl_hours: int = 168
```

## Running the Demo

### Prerequisites

1. ExoArmur V1 system running with golden demo
2. Federation handshake completed between federates
3. Feature flags enabled for coordination visibility

### Step 1: Enable Features

```python
# Enable observation ingest
ingest_config.feature_enabled = True

# Enable belief aggregation
belief_config.feature_enabled = True
```

### Step 2: Create Observations

```python
# Create telemetry summary observation
observation = ObservationV1(
    observation_id="obs-demo-001",
    source_federate_id="cell-us-east-1-cluster-01",
    timestamp_utc=datetime.now(timezone.utc),
    correlation_id="demo-correlation-001",
    nonce="demo-nonce-001",
    observation_type=ObservationType.TELEMETRY_SUMMARY,
    confidence=0.85,
    evidence_refs=["telemetry-source-1"],
    payload=TelemetrySummaryPayloadV1(
        event_count=150,
        time_window_seconds=300,
        event_types=["process_start", "network_connect"],
        severity_distribution={"low": 120, "medium": 30}
    )
)

# Sign observation
signed_observation = sign_message(observation, private_key)

# Ingest observation
success, reason, audit_event = ingest_service.ingest_observation(signed_observation)
```

### Step 3: Aggregate Beliefs

```python
# Aggregate beliefs from observations
beliefs = belief_service.aggregate_observations(
    observation_type=ObservationType.TELEMETRY_SUMMARY
)

print(f"Created {len(beliefs)} beliefs")
for belief in beliefs:
    print(f"Belief {belief.belief_id}: {belief.evidence_summary}")
```

### Step 4: Query via API

```python
# List observations
response = client.get("/api/v2/visibility/observations")
observations = response.json()

# Get timeline for correlation
response = client.get("/api/v2/visibility/timeline/demo-correlation-001")
timeline = response.json()

print(f"Timeline has {len(timeline['observations'])} observations and {len(timeline['beliefs'])} beliefs")
```

## Testing

### Running Tests

```bash
# Run observation ingest tests
python -m pytest tests/test_observation_ingest.py -v

# Run belief aggregation tests
python -m pytest tests/test_belief_aggregation.py -v

# Run visibility API tests
python -m pytest tests/test_visibility_api.py -v

# Run all coordination visibility tests
python -m pytest tests/test_observation_*.py tests/test_belief_*.py tests/test_visibility_*.py -v
```

### Key Tests

1. **test_observation_ingest_requires_confirmed_federate** - Ensures only confirmed federates can submit
2. **test_observation_signature_required_and_verified** - Validates signature verification
3. **test_belief_aggregation_is_deterministic** - Ensures deterministic aggregation
4. **test_visibility_endpoints_return_provenance** - Validates provenance in API responses
5. **test_replay_reproduces_same_beliefs_from_same_observations** - Ensures replay capability

## Security Considerations

### Authentication & Authorization

- **Federate Confirmation**: Only federates with successful handshakes can submit
- **Signature Verification**: All observations must be cryptographically signed
- **Nonce Replay Protection**: Prevents replay attacks with nonce tracking

### Data Validation

- **Schema Validation**: Strict Pydantic model validation
- **Type Safety**: No dict soup - all payloads are typed
- **Size Limits**: Maximum observation size enforced

### Audit Trail

- **Complete Provenance**: Every observation and belief tracked
- **Correlation Links**: Full timeline by correlation ID
- **Replay Capability**: System can replay to reproduce beliefs

## Monitoring & Operations

### Metrics to Monitor

- Observation ingest rate and success/failure ratios
- Belief aggregation performance and output rates
- Storage utilization and cleanup effectiveness
- API response times and error rates

### Operational Tasks

- **Cleanup**: Expired observations and beliefs automatically cleaned
- **Conflict Resolution**: Manual review and arbitration of belief conflicts
- **Performance Tuning**: Adjust aggregation windows and thresholds

## Troubleshooting

### Common Issues

1. **Observations Rejected**: Check federate confirmation status and signatures
2. **No Beliefs Generated**: Check feature flags and observation types
3. **API Timeouts**: Check storage performance and query efficiency
4. **Replay Failures**: Verify deterministic aggregation and nonce handling

### Debug Commands

```python
# Check ingest statistics
stats = ingest_service.get_ingest_statistics()
print(f"Ingest stats: {stats}")

# Check store statistics
stats = observation_store.get_statistics()
print(f"Store stats: {stats}")

# Check aggregation statistics
stats = belief_service.get_aggregation_statistics()
print(f"Aggregation stats: {stats}")
```

## Future Enhancements

### Potential V2+ Features

1. **Advanced Correlation**: Cross-correlation of observations
2. **Machine Learning**: ML-based belief derivation
3. **Real-time Streaming**: Real-time observation processing
4. **Distributed Storage**: Scalable distributed storage backend
5. **Advanced Analytics**: Complex belief relationships and patterns

### Backward Compatibility

All V2 features are additive and can be safely disabled without affecting V1 functionality. The system maintains full compatibility with existing V1 deployments.
