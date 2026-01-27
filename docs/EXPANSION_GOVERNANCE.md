# ExoArmur Expansions Governance Policy

## Purpose

This document defines the governance boundaries and scope controls for ExoArmur expansions development. All development must operate within these constraints to maintain system integrity and prevent scope drift.

## Out-of-Scope Items (HARD BOUNDARIES)

The following items are explicitly **OUT OF SCOPE** for the ExoArmur expansions project:

### 1. Automated Response/Enforcement
- **PROHIBITED**: Any automated execution of containment or response actions
- **ALLOWED**: Analysis, hypothesis generation, narrative creation, timeline reconstruction
- **RATIONALE**: Preserves human-in-the-loop safety model

### 2. Federation/Control Plane Implementation  
- **PROHIBITED**: Implementation of federation protocols, control plane APIs, or distributed coordination
- **ALLOWED**: Use of existing V1 federation capabilities only
- **RATIONALE**: Focus on analytical capabilities, not infrastructure

### 3. Network Calls in CI/Testing
- **PROHIBITED**: Any network requests during CI pipeline execution
- **ALLOWED**: Local testing with mocked/stubbed external dependencies
- **RATIONALE**: Ensures deterministic, reproducible testing

### 4. LLM as Source of Truth
- **PROHIBITED**: Using LLM outputs as factual evidence without verification
- **ALLOWED**: LLM assistance in code generation and analysis patterns
- **RATIONALE**: Maintains evidence-based decision making

### 5. Future Scaffolding or Placeholders
- **PROHIBITED**: Adding "TODO" items, stub functions, or placeholder implementations
- **ALLOWED**: Complete, testable implementations or explicit NotImplementedError with failing tests
- **RATIONALE**: Prevents accumulation of technical debt

## In-Scope Items (EXPANSION FOCUS)

The following items are **IN SCOPE** for the ExoArmur expansions project:

### 1. Temporal Module (exoarmur_temporal)
- **FOCUS**: Belief evolution over time
- **CAPABILITIES**: 
  - Decay, reinforcement, contradiction handling
  - BeliefDeltaV1 emission with EvidenceRefV1 citations
  - Deterministic temporal analysis
- **BOUNDARIES**: Analysis only, no automated actions

### 2. Analyst Module (exoarmur_analyst)  
- **FOCUS**: Autonomous analysis and narrative generation
- **CAPABILITIES**:
  - Hypothesis generation from beliefs
  - NarrativeV1 and FindingV1 creation
  - Evidence-backed claim validation
- **BOUNDARIES**: No execution capabilities, citation-required outputs

### 3. Forensics Module (exoarmur_forensics)
- **FOCUS**: Timeline reconstruction and conflict identification
- **CAPABILITIES**:
  - Deterministic timeline building
  - ConflictV1 emission for uncertainty representation
  - Bounded timestamp skew analysis
- **BOUNDARIES**: Analysis only, no remediation actions

## Development Constraints

### Core V1 Immutability
- **RULE**: No modifications to V1 runtime behavior or contracts
- **ALLOWED**: Additive shared contracts only
- **ENFORCEMENT**: Golden Demo must continue passing unchanged

### Evidence Discipline
- **RULE**: Every analytical claim must cite EvidenceRefV1
- **ENFORCEMENT**: Automated validation rejects uncited claims
- **STANDARD**: Binary green tests only, no skipped tests

### Determinism Requirements
- **RULE**: All outputs must be deterministic and reproducible
- **ENFORCEMENT**: Golden scenario snapshot stability gates
- **STANDARD**: Same inputs must produce identical outputs

## Quality Gates

### Binary Green Testing
- **REQUIREMENT**: All tests must pass, no skipped tests allowed
- **ENFORCEMENT**: CI pipeline fails on any skipped test
- **RATIONALE**: Prevents hiding broken functionality

### Schema Snapshot Stability
- **REQUIREMENT**: Shared primitive schemas must remain stable
- **ENFORCEMENT**: Automated hash comparison in CI
- **RATIONALE**: Maintains contract compatibility across modules

### Coverage Requirements
- **REQUIREMENT**: Minimum 80% test coverage
- **ENFORCEMENT**: CI pipeline fails below threshold
- **RATIONALE**: Ensures adequate testing of new functionality

## Change Control

### Scope Change Process
1. **PROPOSAL**: Written justification for scope expansion
2. **REVIEW**: Architecture committee review
3. **APPROVAL**: Explicit governance approval required
4. **DOCUMENTATION**: Update this governance policy

### Emergency Exceptions
- **PROCESS**: Document emergency, implement temporary fix, schedule proper solution
- **REQUIREMENT**: Must be approved by safety team lead
- **FOLLOW-UP**: Permanent solution within 30 days

## Compliance Verification

### Automated Checks
- Schema snapshot stability verification
- No-skipped-tests enforcement
- Coverage threshold validation
- Code formatting and type checking

### Manual Reviews
- Architecture compliance for new components
- Security review for any data handling changes
- Performance impact assessment for core changes

## Enforcement

### CI Pipeline Gates
- All verification scripts must pass
- Any failure blocks merge/deployment
- Failures require explicit resolution

### Development Discipline
- Code reviews must check scope compliance
- Architects must validate contract changes
- Safety team must review any V1-adjacent changes

## Consequences

### Scope Violations
- **FIRST OFFENSE**: Warning and immediate remediation
- **REPEAT OFFENSE**: Development access suspension
- **SEVERE VIOLATIONS**: Project removal and security review

### Quality Failures
- **TEST FAILURES**: Block deployment until resolution
- **COVERAGE GAPS**: Require additional test coverage
- **DRIFT ISSUES**: Rollback to last stable state

---

**VERSION**: 1.0  
**EFFECTIVE**: 2025-01-27  
**REVIEW**: Quarterly or after major architectural changes  
**APPROVED**: ExoArmur Architecture Committee  

*This policy is enforceable and binding on all ExoArmur expansions development activities.*
