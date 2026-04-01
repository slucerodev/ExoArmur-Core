# ExoArmur Public Traction Demo

## Overview

This directory contains minimal, self-contained demos that demonstrate ExoArmur's core value proposition without requiring technical expertise.

## Current Demos

### 1. Tamper Detection Demo (`tamper_detection_demo.py`)

**What it shows**: How ExoArmur detects when audit events have been tampered with, even by insider threats.

**Scenario**: Financial transaction audit trail with potential fraud
- Clean audit trail → All nodes agree (consensus achieved)
- Tampered audit trail → System detects divergent nodes
- Clear identification of which systems are compromised

**Business Value**: 
- Detects financial record tampering
- Identifies compromised data sources
- Maintains audit integrity for regulatory compliance
- Provides cryptographic proof of tampering

**Runtime**: ~30 seconds

## How to Run

```bash
# From ExoArmur root directory
source .venv/bin/activate
python demo/tamper_detection_demo.py
```

## Expected Output

The demo produces clear, human-readable output showing:

```
🛡️  ExoArmur Tamper Detection Demo
Demonstrating Byzantine fault tolerance in audit trail verification

============================================================
 SCENARIO 1: Clean Audit Trail
============================================================
All nodes receive identical, untampered audit events

🔍 Clean Audit Trail Results:
   Consensus: ✅ ACHIEVED
   All 5 nodes in agreement
   Hash Patterns:
     a1b2c3d4... → node-1, node-2, node-3, node-4, node-5

============================================================
 SCENARIO 2: Tampered Audit Trail
============================================================
Node 4 and Node 5 receive tampered events (simulating insider threat)

🔍 Tampered Audit Trail Results:
   Consensus: ❌ FAILED
   Divergent Nodes: 2
     - node-4
     - node-5
   Consensus Nodes: 3
     - node-1
     - node-2
     - node-3
   Hash Patterns:
     a1b2c3d4... → node-1, node-2, node-3
     e5f6g7h8... → node-4
     i9j0k1l2... → node-5

============================================================
 DETECTION SUMMARY
============================================================
🎯 Key Findings:
   ✅ Clean audit trail: All nodes agree
   ✅ Tampering detected: System identified divergent nodes
   📊 Detection accuracy: 2/2 tampered nodes caught
   🔒 System integrity: Byzantine fault tolerance working correctly

============================================================
 BUSINESS VALUE
============================================================
💡 What this means for your organization:
   • Detects when financial records have been altered
   • Identifies which systems/data sources are compromised
   • Maintains audit integrity even with insider threats
   • Provides cryptographic proof of tampering
   • Enables regulatory compliance with immutable audit trails

🚀 Demo completed successfully!
   Total nodes simulated: 5
   Byzantine tolerance: Up to 1 compromised nodes
   Detection method: TRACE_IDENTITY_HASH consensus verification
```

## Technical Foundation

These demos are built on ExoArmur's production-stable Multi-Node Replay Verifier:

- **TRACE_IDENTITY_HASH**: Cryptographic hash including correlation_id for audit trails
- **Byzantine Fault Tolerance**: Tolerates up to ⌊(n-1)/3⌋ compromised nodes
- **Deterministic Consensus**: Identical inputs always produce identical outputs
- **No Single Point of Trust**: Distributed verification across multiple nodes

## Demo Design Principles

1. **Minimal Reproducible**: Single script, no setup required
2. **Business Context**: Real-world scenarios (financial, healthcare, etc.)
3. **Clear Before/After**: Shows system state with and without issues
4. **No Code Reading Required**: Output explains the value proposition
5. **Fast Execution**: Under 5 minutes total runtime

## Future Demos (Planned)

- **Consensus Divergence**: Network partition scenarios
- **Replay Inconsistency**: Data corruption detection
- **Regulatory Compliance**: Audit trail verification for compliance reporting

## Integration Notes

These demos use only ExoArmur Core components:
- `MultiNodeReplayVerifier`
- `CanonicalEvent` system
- `TRACE_IDENTITY_HASH` consensus logic

No additional modules, databases, or infrastructure required.