# ExoArmur ADMO - Deterministic Audit Replay Protocol

**Purpose**: Ensure complete reproducibility and verification of organism behavior through deterministic audit replay.

## **Overview**

The ExoArmur replay system provides deterministic reconstruction of organism behavior from audit logs. This enables:

- **Verification**: Prove that executed actions match approved intents
- **Compliance**: Demonstrate adherence to safety and authority rules  
- **Debugging**: Replay incidents to understand decision pathways
- **Forensics**: Investigate anomalies with complete evidence trails

## **Core Principles**

### **Determinism First**
- Same audit logs → same replay results every time
- Canonical serialization eliminates ordering ambiguities
- Stable hashing provides immutable intent verification

### **Authority Preservation**
- All replay respects original authority boundaries
- Intent binding verification prevents tampering
- Safety gate re-evaluation confirms consistent decisions

### **Complete Evidence Chain**
- Every meaningful state transition emits audit events
- Payload integrity verification prevents undetected mutations
- End-to-end traceability from telemetry to execution

## **Architecture**

### **1. Canonical Event Envelope**

```python
@dataclass(frozen=True)
class AuditEventEnvelope:
    event_id: str
    timestamp: datetime
    event_type: str
    actor: str
    correlation_id: str
    payload: Dict[str, Any]
    payload_hash: str
    sequence_number: Optional[int] = None
    parent_event_id: Optional[str] = None
    # ... metadata fields
```

**Key Features**:
- **Deterministic Ordering**: `(timestamp, event_type_priority, event_id, sequence_number)`
- **Payload Integrity**: SHA-256 hash of canonical JSON payload
- **Event Type Priority**: Ensures consistent processing order

### **2. Canonical Serialization**

```python
def canonical_json(data: Any) -> str:
    """Convert data to canonical JSON representation"""
    # Sort object keys alphabetically
    # Normalize datetime to UTC ISO format
    # Handle special float values (NaN, inf) consistently
    # Use compact separators (no whitespace)
```

**Rules**:
- Object keys sorted alphabetically
- Datetime normalized to UTC ISO format
- Special floats (`NaN`, `inf`, `-inf`) → `"null"`
- Compact JSON with no whitespace

### **3. Stable Hashing**

```python
def stable_hash(data: str) -> str:
    """Generate SHA-256 hash of canonical data"""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
```

**Applications**:
- Intent hash binding verification
- Payload integrity checking
- Deterministic state reconstruction

### **4. Replay Engine**

```python
class ReplayEngine:
    def replay_correlation(self, correlation_id: str) -> ReplayReport:
        """Deterministic replay of audit trail"""
        # 1. Retrieve audit records
        # 2. Convert to canonical envelopes
        # 3. Sort by deterministic ordering
        # 4. Process events in sequence
        # 5. Verify state integrity
        # 6. Generate comprehensive report
```

## **Event Processing Pipeline**

### **Event Types & Priorities**

| Priority | Event Type | Description |
|----------|------------|-------------|
| 1 | `telemetry_ingested` | Telemetry event received |
| 2 | `safety_gate_evaluated` | Safety gate decision made |
| 3 | `approval_requested` | Human/quorum approval required |
| 4 | `approval_bound_to_intent` | Intent frozen and bound to approval |
| 5 | `intent_denied` | Intent execution denied |
| 6 | `intent_executed` | Intent successfully executed |
| 7 | `approval_approved` | Approval granted |
| 8 | `approval_denied` | Approval rejected |

### **Processing Logic**

#### **Telemetry Ingested**
- Reconstruct original telemetry event
- Validate required fields (event_id, correlation_id, trace_id)
- Verify payload integrity

#### **Safety Gate Evaluated**  
- Reconstruct safety gate verdict
- Store verdict for later verification
- Validate rationale and rule references

#### **Approval Requested**
- Reconstruct approval request details
- Extract approval_id for intent binding
- Verify approval context

#### **Intent Binding**
- **Critical**: Verify intent hash matches stored intent
- Reconstruct intent from IntentStore if available
- Validate approval-intent binding integrity

#### **Intent Executed**
- Reconstruct executed intent
- **Critical**: Verify hash matches approved intent
- Validate execution context and parameters

## **Verification Rules**

### **Intent Hash Verification**
```python
def verify_intent_binding(approval_id: str, intent: ExecutionIntentV1) -> bool:
    """Verify executed intent matches approved intent"""
    stored_hash = intent_store.get_bound_intent_hash(approval_id)
    computed_hash = intent_store.compute_intent_hash(intent)
    return stored_hash == computed_hash
```

### **Safety Gate Consistency**
```python
def verify_safety_gate_consistency(original_verdict: str, 
                                 reconstructed_inputs: Dict) -> bool:
    """Re-evaluate safety gate with same inputs"""
    reconstructed_verdict = safety_gate.evaluate_safety(**reconstructed_inputs)
    return original_verdict == reconstructed_verdict.verdict
```

### **Payload Integrity**
```python
def verify_payload_integrity(envelope: AuditEventEnvelope) -> bool:
    """Verify payload matches stored hash"""
    canonical_payload = canonical_json(envelope.payload)
    computed_hash = stable_hash(canonical_payload)
    return computed_hash == envelope.payload_hash
```

## **Replay Report Structure**

```python
@dataclass
class ReplayReport:
    correlation_id: str
    result: ReplayResult  # SUCCESS/FAILURE/PARTIAL
    
    # Processing metrics
    total_events: int
    processed_events: int
    failed_events: int
    
    # Verification results
    intent_hash_verified: bool
    safety_gate_verified: bool
    audit_integrity_verified: bool
    
    # Reconstructed state
    reconstructed_intents: Dict[str, ExecutionIntentV1]
    safety_gate_verdicts: Dict[str, str]
    
    # Issues found
    failures: List[str]
    warnings: List[str]
```

## **CLI Usage**

### **Basic Replay**
```bash
python -m src.replay.cli run <correlation_id> --audit-store audit.json
```

### **Generate Envelopes**
```bash
python -m src.replay.cli envelope audit.json --output envelopes.json
```

### **Compute Hash**
```bash
python -m src.replay.cli hash data.json
```

## **Testing Requirements**

### **Unit Tests**
- Canonical serialization deterministic behavior
- Stable hash consistency
- Event envelope creation and validation
- Replay engine individual components

### **Integration Tests**
- End-to-end replay verification
- Intent hash reconstruction
- Safety gate consistency checking
- Payload integrity verification

### **Regression Tests**
- Replay produces same results across versions
- Hash stability for known intents
- Event ordering determinism

## **Failure Modes**

### **Replay Failure Conditions**
- Missing audit records
- Payload hash mismatches (tampering detected)
- Intent hash mismatches (binding violations)
- Missing intent store references
- Corrupted event envelopes

### **Partial Success Conditions**
- Some events fail processing
- Warnings for non-critical issues
- Missing optional verification data

### **Handling Strategies**
- **Fail Fast**: Critical integrity violations → FAILURE
- **Graceful Degradation**: Non-critical issues → WARNINGS
- **Complete Verification**: All checks pass → SUCCESS

## **Security Considerations**

### **Tamper Detection**
- Payload hash verification prevents undetected modifications
- Canonical serialization eliminates ambiguity attacks
- Deterministic ordering prevents replay manipulation

### **Privacy Protection**
- Sensitive payload data handled securely
- Hash verification without exposing full content
- Audit trail access controlled by authorization

### **Integrity Guarantees**
- Cryptographic hash verification (SHA-256)
- End-to-end traceability maintained
- No silent state transitions possible

## **Performance Considerations**

### **Optimization Strategies**
- Lazy loading of audit records
- Parallel processing of independent events
- Cached canonical computations
- Efficient hash verification

### **Scalability Limits**
- Large audit trails processed in chunks
- Memory usage bounded by event window size
- I/O optimized for sequential access patterns

## **Integration Points**

### **IntentStore Integration**
```python
# Enhanced intent hashing uses canonical utilities
def compute_intent_hash(self, intent: ExecutionIntentV1) -> str:
    intent_dict = intent.model_dump()
    # Remove volatile fields
    for field in ['created_at', 'updated_at', 'execution_started_at', 'execution_completed_at']:
        intent_dict.pop(field, None)
    
    canonical_representation = canonical_json(intent_dict)
    return stable_hash(canonical_representation)
```

### **AuditLogger Integration**
```python
# Enhanced audit records include payload hashes
def emit_audit_record(self, event_kind: str, payload_ref: Dict[str, Any], ...):
    audit_record = AuditRecordV1(
        # ... other fields
        hashes={
            "sha256": self._compute_hash(payload_ref),
            "upstream_hashes": []
        },
        # ...
    )
```

## **Future Enhancements**

### **Planned Features**
- Distributed replay across multiple cells
- Real-time replay streaming
- Machine learning anomaly detection in replay patterns
- Enhanced visualization of replay timelines

### **Extension Points**
- Custom event type processors
- Additional verification rules
- Alternative serialization formats
- External verification services

---

**This protocol ensures ExoArmur maintains complete determinism and verifiability across all organism operations.**
