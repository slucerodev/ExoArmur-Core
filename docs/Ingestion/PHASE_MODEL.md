# PHASE_MODEL.md

## Purpose
Defines the operational phases of ExoArmur from initial deployment through continuous operation, including phase transitions and capability evolution.

## Definitions

**Phase**: A distinct operational state of the ExoArmur system with specific capabilities, constraints, and transition criteria.

**Phase Transition**: The movement from one operational phase to another based on satisfaction of predefined criteria.

**Bootstrap Phase**: Initial system startup and basic capability verification before defensive operations begin.

**Operational Phase**: Normal defensive operations with full capability deployment and continuous threat response.

**Degraded Phase**: Reduced capability operations due to system failures, network partitions, or resource constraints.

**Recovery Phase**: System restoration from degraded or failed states back to normal operational capability.

**Maintenance Phase**: Planned system updates, configuration changes, or capability upgrades with controlled impact.

**Emergency Phase**: Crisis response operations with modified rules of engagement and escalated approval requirements.

**Partition Mode**: Operational state during network disruptions where cells operate with cached policies and local decision making.

**Quorum Mode**: Operational state requiring collective confidence from multiple cells for high-impact actions.

**Human Override Mode**: Operational state requiring explicit human approval for actions normally allowed autonomously.

## Phase Definitions and Characteristics

### Phase 0: Bootstrap
**Purpose**: System initialization and basic capability verification
**Duration**: Until all health checks pass and basic capabilities verified
**Capabilities**:
- Health endpoint responding
- Basic telemetry ingestion functional
- Policy bundle loading and verification
- Safety gate operational
- Audit logging functional
**Constraints**:
- No defensive actions beyond A0 observation
- No belief propagation to other cells
- No collective confidence operations
- No execution beyond basic system validation
**Transition Criteria**:
- All health checks pass
- Policy bundle verified and loaded
- Safety gate responds correctly
- Audit system functional
- Basic telemetry processing validated

### Phase 1: Operational
**Purpose**: Normal defensive operations with full capabilities
**Duration**: Continuous until system state changes
**Capabilities**:
- Full telemetry ingestion and processing
- Complete belief propagation and collective confidence
- All action classes available with proper authorization
- Full safety gate enforcement
- Complete audit and compliance capabilities
- Multi-cell coordination and quorum formation
**Constraints**:
- All safety invariants must be satisfied
- Policy authorization required for all execution
- Trust constraints enforced for autonomy
- Confidence thresholds maintained
**Transition Criteria**:
- System health degrades (to Degraded Phase)
- Network partition detected (to Partition Mode)
- Maintenance window begins (to Maintenance Phase)
- Emergency declared (to Emergency Phase)

### Phase 2: Degraded
**Purpose**: Reduced capability operations during system stress or failures
**Duration**: Until underlying issues resolved
**Capabilities**:
- Basic telemetry ingestion (may be rate-limited)
- Local decision making with cached policies
- A0/A1 actions only (unless explicitly authorized)
- Limited belief propagation (may be delayed)
- Basic audit functionality
**Constraints**:
- Severity ladder enforced strictly
- No A2/A3 actions without explicit authorization
- Collective confidence operations suspended
- Trust constraints tightened
**Transition Criteria**:
- System health restored (to Operational Phase)
- Further degradation (to Recovery Phase)
- Maintenance initiated (to Maintenance Phase)

### Phase 3: Recovery
**Purpose**: System restoration from failures or degraded states
**Duration**: Until full capability restored
**Capabilities**:
- Diagnostic and repair operations
- Component restart and reconfiguration
- Data synchronization and reconciliation
- Gradual capability restoration
- Health monitoring and validation
**Constraints**:
- No defensive actions during active recovery
- System may be in maintenance mode
- Audit continuity preserved
- Safety invariants maintained
**Transition Criteria**:
- Full system health restored (to Operational Phase)
- Recovery fails (to Emergency Phase)
- Partial recovery (to Degraded Phase)

### Phase 4: Maintenance
**Purpose**: Planned system updates and capability changes
**Duration**: Planned maintenance window
**Capabilities**:
- Configuration updates and policy changes
- Software updates and patches
- Capability additions or modifications
- System restarts and reconfigurations
- Validation and testing
**Constraints**:
- Defensive actions may be limited
- System may operate in reduced capacity
- Rollback capability maintained
- Audit continuity preserved
**Transition Criteria**:
- Maintenance completed successfully (to Operational Phase)
- Maintenance fails (to Recovery Phase)
- Emergency during maintenance (to Emergency Phase)

### Phase 5: Emergency
**Purpose**: Crisis response with modified operational rules
**Duration**: Until emergency resolved
**Capabilities**:
- Enhanced monitoring and alerting
- Escalated approval requirements
- Human-in-the-loop decision making
- Emergency response procedures
- Crisis communication and reporting
**Constraints**:
- Autonomous actions may be restricted
- Human approval required for more actions
- Safety invariants never suspended
- Audit requirements intensified
**Transition Criteria**:
- Emergency resolved (to Operational Phase)
- Emergency escalates (to external response)
- System failure during emergency (to Recovery Phase)

## Special Operational Modes

### Partition Mode
**Trigger**: Network partition detected
**Behavior**: Cells operate independently with cached policies
**Duration**: Until partition heals
**Capabilities**:
- Local decision making with cached policies
- A0/A1 actions based on local confidence
- Belief buffering for later propagation
- Basic audit and logging
**Constraints**:
- No collective confidence operations
- No A2/A3 without explicit policy authorization
- No quorum formation possible
- Trust constraints based on last known state

### Quorum Mode
**Trigger**: High-impact actions requiring collective confidence
**Behavior**: Multiple cells must agree before execution
**Duration**: Per action or sustained based on threat level
**Capabilities**:
- Collective confidence aggregation
- Quorum formation and validation
- Distributed decision making
- Enhanced evidence requirements
**Constraints**:
- Minimum distinct cell requirements
- Aggregate confidence thresholds
- Conflict detection and resolution
- Trust-weighted confidence calculations

### Human Override Mode
**Trigger**: Policy configuration or safety requirements
**Behavior**: Human approval required for specified actions
**Duration**: Configurable based on policy
**Capabilities**:
- Human approval workflows
- Enhanced audit trails
- Escalation procedures
- Manual decision interfaces
**Constraints**:
- No execution without human approval
- Time limits for approval responses
- Fallback to safer behaviors if no approval
- Complete documentation of decisions

## Phase Transition Rules

### Allowed Transitions
- Bootstrap → Operational (when all criteria satisfied)
- Operational → Degraded (when system health degrades)
- Operational → Maintenance (when planned maintenance begins)
- Operational → Emergency (when emergency declared)
- Degraded → Operational (when health restored)
- Degraded → Recovery (when further degradation)
- Recovery → Operational (when fully restored)
- Recovery → Degraded (when partial recovery)
- Maintenance → Operational (when completed successfully)
- Maintenance → Recovery (when maintenance fails)
- Emergency → Operational (when emergency resolved)

### Forbidden Transitions
- Bootstrap → Any phase except Operational (must complete initialization)
- Operational → Recovery (must pass through Degraded first)
- Degraded → Emergency (must pass through Recovery first)
- Recovery → Bootstrap (cannot revert to initialization)
- Maintenance → Emergency (must pass through Recovery first)
- Emergency → Bootstrap (cannot revert to initialization)

### Transition Validation
- All phase transitions must be logged
- System state must be validated during transitions
- Audit continuity must be preserved
- Safety invariants must never be violated
- Capability changes must be documented

## Phase-Specific Behaviors

### Bootstrap Phase Behaviors
- System health checks and validation
- Policy bundle loading and verification
- Safety gate initialization and testing
- Basic telemetry processing validation
- Audit system initialization
- No defensive actions beyond observation

### Operational Phase Behaviors
- Full defensive capability deployment
- Normal threat response and containment
- Collective confidence and quorum operations
- Complete audit and compliance reporting
- Multi-cell coordination and belief propagation
- All action classes available with proper authorization

### Degraded Phase Behaviors
- Reduced capability operations
- Severity ladder strict enforcement
- Local decision making priority
- Limited belief propagation
- Enhanced monitoring and alerting
- Conservative action selection

### Recovery Phase Behaviors
- Diagnostic and repair operations
- Component restart and reconfiguration
- Data synchronization and reconciliation
- Gradual capability restoration
- Health monitoring and validation
- Minimal defensive actions only

### Maintenance Phase Behaviors
- Configuration updates and policy changes
- Software updates and patches
- Capability additions or modifications
- System restarts and reconfigurations
- Validation and testing
- Controlled defensive capability

### Emergency Phase Behaviors
- Enhanced monitoring and alerting
- Escalated approval requirements
- Human-in-the-loop decision making
- Emergency response procedures
- Crisis communication and reporting
- Safety invariant enforcement

## Example

Phase transition during system stress:

1. **Operational Phase**: Normal operations with full capabilities
2. **Degradation Detection**: System health monitoring detects resource exhaustion
3. **Phase Transition**: System enters Degraded Phase
4. **Degraded Operations**: 
   - Actions limited to A0/A1 only
   - Severity ladder enforced strictly
   - Collective confidence suspended
5. **Recovery Initiated**: System resources restored
6. **Phase Transition**: System returns to Operational Phase
7. **Operational Resumption**: Full capabilities restored

## Non-Example

Improper phase transition during emergency:

1. **Emergency Declared**: System enters Emergency Phase
2. **Direct Transition**: Attempts to return to Bootstrap Phase
3. **Violation**: Bypasses Recovery Phase requirements
4. **Consequence**: System state not properly validated
5. **Risk**: Potential for inconsistent system state

This violates phase model rules by attempting an invalid transition that bypasses required validation and recovery steps.
