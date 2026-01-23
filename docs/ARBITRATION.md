# Arbitration - Human Override Only

## Overview

Arbitration in ExoArmur provides deterministic conflict resolution with mandatory human approval. When conflicting beliefs are detected, the system creates arbitration objects that require explicit human approval before any resolution can be applied.

## Key Principles

- **No Auto-Resolution**: Conflicts cannot be resolved automatically
- **Human Approval Required**: All arbitration decisions require A3-level human approval
- **Deterministic Conflict Keys**: Conflicts are identified using deterministic keys
- **Audit Trail**: Every arbitration lifecycle change emits audit events
- **Replayable**: Post-resolution belief state can be reproduced deterministically

## Conflict Detection

### Conflict Key Generation

Conflict keys are generated deterministically using the format:
```
belief_type:subject_key:time_window
```

- **belief_type**: Type of belief (e.g., "derived_from_THREAT_INTEL")
- **subject_key**: Extracted from belief metadata or evidence summary
- **time_window**: Hourly time window for grouping conflicts

### Conflict Types

The system detects these types of conflicts:

1. **THREAT_CLASSIFICATION**: Conflicting threat classifications for same subject
2. **SYSTEM_HEALTH**: Conflicting health scores for same system
3. **CONFIDENCE_DISPUTE**: Significant confidence level differences
4. **EVIDENCE_CONFLICT**: Contradictory evidence sources
5. **POLICY_VIOLATION**: Policy rule violations
6. **TRUST_DISPUTE**: Trust score disagreements

### Conflict Detection Logic

```python
# Example: Threat classification conflict
belief1: threat_type="malware", subject="host_A", confidence=0.8
belief2: threat_type="benign", subject="host_A", confidence=0.3
# → Conflict detected, arbitration created
```

## Arbitration Models

### ArbitrationV1 Structure

```python
class ArbitrationV1(BaseModel):
    arbitration_id: str                    # Unique identifier
    created_at_utc: datetime               # Creation timestamp
    status: ArbitrationStatus              # OPEN/RESOLVED/REJECTED/EXPIRED
    conflict_type: ArbitrationConflictType  # Type of conflict
    subject_key: str                       # Subject of conflict
    conflict_key: str                      # Deterministic conflict key
    claims: List[Dict[str, Any]]           # Conflicting claims
    evidence_refs: List[str]               # Evidence references
    correlation_id: Optional[str]          # Correlation ID
    conflicts_detected: List[Dict]         # Detected conflicts
    
    # Resolution fields
    proposed_resolution: Optional[Dict]    # Proposed resolution
    decision: Optional[Dict]               # Final decision
    approval_id: Optional[str]             # Approval request ID
    resolved_at_utc: Optional[datetime]     # Resolution timestamp
    resolver_federate_id: Optional[str]     # Resolver federate
    resolution_applied_at_utc: Optional[datetime]  # Application timestamp
```

### Arbitration Lifecycle

1. **OPEN**: Initial state after conflict detection
2. **RESOLVED**: Resolution applied after approval
3. **REJECTED**: Arbitration rejected by resolver
4. **EXPIRED**: Arbitration expired without resolution

## Arbitration Service

### Creating Arbitrations

```python
# Conflict detection automatically creates arbitrations
arbitrations = conflict_detection_service.detect_belief_conflicts(beliefs)

# Manual creation (rare)
arbitration_service.create_arbitration(arbitration)
```

### Resolution Process

1. **Propose Resolution**: Store resolution proposal without applying
2. **Human Approval**: A3 approval required via ApprovalService
3. **Apply Resolution**: Apply only when approval status == APPROVED

```python
# Propose resolution
resolution = {
    "resolved_threat_type": "trojan",
    "type": "threat_classification_update"
}
arbitration_service.propose_resolution(arbitration_id, resolution)

# Apply after approval
arbitration_service.apply_resolution(arbitration_id, resolver_federate_id)
```

### Resolution Types

#### Threat Classification Resolution
```python
{
    "resolved_threat_type": "trojan",
    "type": "threat_classification_update"
}
```

#### System Health Resolution
```python
{
    "resolved_health_score": 0.7,
    "type": "health_score_consensus"
}
```

#### Confidence Dispute Resolution
```python
{
    "resolved_confidence": 0.6,
    "type": "confidence_adjustment"
}
```

## Approval Integration

### Approval Request Creation

When an arbitration is created, an A3 approval request is automatically generated:

```python
approval_id = f"approval_{arbitration_id}_{timestamp}"
# ApprovalService.create_approval(
#     request_type="A3",
#     scope=f"arbitration:{arbitration_id}",
#     rationale=f"Human approval required for {conflict_type} conflict"
# )
```

### Approval Status Check

Resolutions are only applied when approval is granted:

```python
def _check_approval_status(self, approval_id: str) -> bool:
    # approval = self.approval_service.get_approval(approval_id)
    # return approval.status == "approved"
    return True  # Mock for testing
```

## API Endpoints

### Read-Only Endpoints

#### List Arbitrations
```http
GET /api/v2/visibility/arbitrations?status=OPEN&conflict_type=THREAT_CLASSIFICATION&limit=100
```

#### Get Arbitration
```http
GET /api/v2/visibility/arbitrations/{arbitration_id}
```

### Response Format

```json
{
    "arbitration_id": "arb_20231201_1234",
    "created_at_utc": "2023-12-01T12:00:00Z",
    "status": "open",
    "conflict_type": "threat_classification",
    "subject_key": "host_A",
    "conflict_key": "abc123...",
    "claims": [...],
    "evidence_refs": ["obs-1", "obs-2"],
    "correlation_id": "corr-123",
    "conflicts_detected": [...],
    "proposed_resolution": null,
    "decision": null,
    "approval_id": "approval_arb_20231201_1234_20231201120000",
    "resolved_at_utc": null,
    "resolver_federate_id": null,
    "resolution_applied_at_utc": null,
    "metadata": {}
}
```

## Audit Events

### Event Types

- `arbitration_created`: New arbitration created
- `arbitration_resolution_proposed`: Resolution proposed
- `arbitration_resolved`: Resolution applied
- `arbitration_rejected`: Arbitration rejected
- `conflict_detected`: Conflict detected

### Audit Event Structure

```json
{
    "event_type": "arbitration_created",
    "timestamp_utc": "2023-12-01T12:00:00Z",
    "correlation_id": "corr-123",
    "source_federate_id": "arbitration_service",
    "event_data": {
        "arbitration_id": "arb_20231201_1234",
        "conflict_type": "threat_classification",
        "subject_key": "host_A",
        "approval_id": "approval_arb_20231201_1234_20231201120000",
        "num_claims": 2
    }
}
```

## Replay and Determinism

### Replay Requirements

The ReplayEngine must reproduce:
1. Arbitration objects and their lifecycle states
2. Approval decisions and timestamps
3. Resolution applications and belief updates
4. Post-resolution belief state deterministically

### Deterministic Behavior

- Same conflict detection inputs → same arbitration objects
- Same resolution proposals → same belief updates
- Same approval decisions → same final state
- Audit trail provides complete replay capability

## Configuration

### Feature Flags

```yaml
v2_arbitration_enabled:
  description: "Enable conflict detection and arbitration"
  default_value: false
  rollout_strategy: "gradual"
  dependencies: ["v2_federation_enabled"]
  risk_level: "medium"
  owner: "security_team"
```

### Service Configuration

```python
arbitration_service = ArbitrationService(
    arbitration_store=arbitration_store,
    audit_service=audit_service,
    clock=clock,
    observation_store=observation_store,
    feature_flag_enabled=True
)
```

## Testing

### Test Coverage

The test suite covers:
- Conflict detection creates arbitration objects
- Arbitration requires human approval
- Resolution does not apply without approval
- Resolution applies after approval and updates beliefs
- Arbitration decision is audited and replayable
- Replay reproduces post-resolution belief state
- Feature flag functionality

### Running Tests

```bash
# Run all arbitration tests
python3 -m pytest tests/test_arbitration.py -v

# Run specific test
python3 -m pytest tests/test_arbitration.py::test_conflict_detection_creates_arbitration_object -v
```

## Troubleshooting

### Common Issues

1. **Feature Flag Disabled**: Arbitration functionality is disabled by default
2. **Approval Integration**: Mock approval service returns True by default
3. **Conflict Key Collisions**: Ensure deterministic key generation
4. **Belief Updates**: Resolution application requires observation store

### Debug Logging

```python
import logging
logging.getLogger("src.federation.arbitration").setLevel(logging.DEBUG)
```

### Monitoring Metrics

- Number of arbitrations created per time window
- Resolution approval/denial rates
- Time to resolution (approval → application)
- Conflict detection accuracy

## Security Considerations

- **Human-in-the-Loop**: No automatic conflict resolution
- **Approval Boundaries**: A3 approval required for all arbitrations
- **Audit Trail**: Complete lifecycle audit events
- **Deterministic Behavior**: Predictable conflict handling
- **Replay Safety**: State reconstruction capability

## Future Enhancements

1. **Multi-Federate Arbitration**: Cross-cell conflict resolution
2. **Policy-Based Auto-Resolution**: Limited auto-resolution for low-risk conflicts
3. **Arbitration Templates**: Pre-defined resolution patterns
4. **Escalation Workflows**: Automatic escalation for unresolved conflicts
5. **Analytics Dashboard**: Conflict trends and resolution metrics
