# Golden Demo Governance Integrity

## Why Golden Demo is Sacred

### Golden Demo Supremacy Principle

The Golden Demo is the **SOLE ACCEPTANCE TEST** for ExoArmur v1. It represents the complete end-to-end scenario that validates the entire ADMO organism functions correctly. This is not just another test - it is the definition of "done" for the entire system.

### Governance Integrity Requirements

**NO MOCK BEHAVIOR ALLOWED:**
- No in-memory belief storage
- No simulated JetStream replay  
- No fake audit reconstruction
- No mock NATS messaging
- No stubbed persistence

**REAL IMPLEMENTATIONS REQUIRED:**
- Actual JetStream belief persistence and replay
- Real audit trail reconstruction from JetStream
- Live NATS messaging between cells
- True partition tolerance testing
- Genuine collective confidence formation

### Why Tests Must Not Lie

**Mock Tests Are NOT Acceptance:**
- Unit tests with mocks validate interfaces only
- Integration tests with in-memory stores validate logic only
- Only the Golden Demo with real JetStream validates complete system behavior

**Failure Is Honest:**
- Golden Demo failure indicates missing real implementation
- xfail(strict=True) ensures the test fails when it unexpectedly passes
- Success must come from real JetStream implementation, not mock removal

### Implementation Requirements

**Before Golden Demo Can Pass:**
1. **Real JetStream Belief Replay**
   - `ExoArmurNATSClient.replay_beliefs()` must query actual JetStream
   - No in-memory `_belief_store` or similar substitutes

2. **Durable Audit Reconstruction**
   - `ExoArmurNATSClient.reconstruct_audit_trail()` must rebuild from JetStream
   - No simulated audit trails or in-memory caches

3. **Live Messaging Between Cells**
   - Actual NATS JetStream publish/subscribe between multiple cells
   - Real partition simulation and healing

4. **True Collective Confidence**
   - Belief aggregation from real JetStream data
   - No pre-computed or mocked confidence scores

### Governance Enforcement

**Current State:**
- Golden Demo is marked `@pytest.mark.xfail(strict=True)`
- NATS client raises `NotImplementedError` for replay/reconstruction methods
- All in-memory storage has been removed
- Test will fail until real JetStream implementation exists

**When Golden Demo Passes:**
- It means real JetStream persistence works
- Actual belief replay functions correctly
- Genuine audit reconstruction succeeds
- Complete end-to-end ADMO loop is validated

### ADMO Organism Law Compliance

**LAW-06: Evidence-Backed Decisions**
- Golden Demo requires real evidence from JetStream, not mock data

**LAW-09: Graceful Degradation**
- System may degrade without JetStream, but Golden Demo requires full functionality

**Golden Demo Law**
- This test is the definition of production readiness
- No shortcuts, no mocks, no simulated success
- Real implementation or honest failure

The Golden Demo remains the sacred gatekeeper of ExoArmur v1 acceptance.
