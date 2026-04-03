# Archived Demo Collection

This directory contains demos that have been superseded by the canonical truth reconstruction demo.

## Superseded By

All demos in this archive are superseded by:
```
demos/canonical_truth_reconstruction_demo.py
```

The canonical demo provides:
- Full end-to-end lifecycle demonstration
- Deterministic output with fixed markers
- Real execution (no mocks for core logic)
- Cryptographic proof bundle generation
- Replay verification capability

## Archived Demos

### V2 Experimental Demos
- `demo_v2_restrained_autonomy.py` - V2 restrained autonomy demo (feature-flagged experimental)
- `demo_api.py` - API testing demo
- `demo_handshake.py` - Federation handshake demo
- `demo_identity_containment.py` - Identity containment demo
- `demo_scenario.py` - Scenario testing demo
- `demo_visibility_arbitration.py` - Visibility arbitration demo
- `demo_web_server.py` - Web server demo

### Research/Experimental Demos
- `demo_tamper_detection.py` - Tamper detection research demo
- `demo_production_drift.py` - Production drift presentation demo

## Why Archived

These demos were archived because:
1. **Redundancy**: Multiple overlapping demos created confusion about "the right way" to run ExoArmur
2. **Fragmentation**: No single demo demonstrated the complete end-to-end capability
3. **Inconsistency**: Different demos used different patterns and approaches
4. **Experimental Focus**: Many demos focused on experimental V2 features rather than core capabilities

## Migration Path

To use the canonical demo:
```bash
python demos/canonical_truth_reconstruction_demo.py
```

Expected output markers:
- `DEMO_RESULT=DENIED`
- `ACTION_EXECUTED=false`
- `AUDIT_STREAM_ID=canonical-truth-reconstruction-demo`
- `Proof bundle written: demos/canonical_proof_bundle.json`

## Notes

- These demos are preserved for historical reference and potential future use
- They may contain useful patterns for specific use cases
- The canonical demo should be used for all general ExoArmur demonstration purposes
