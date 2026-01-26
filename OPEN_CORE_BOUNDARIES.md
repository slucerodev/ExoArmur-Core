# ExoArmur Open-Core Boundary Definition

## � RUNTIME & ARTIFACTS POLICY

### Repository Hygiene
- **data/**: NATS JetStream runtime state - generated locally, excluded from Git
- **artifacts/reality_run_**/**: Evidence bundles - reproducible, not stored in Git  
- **__pycache__/**, *.pyc: Python bytecode - excluded from Git
- **.venv/**: Virtual environments - excluded from Git
- **logs/**: Runtime logs - excluded from Git

### Reproducibility Guarantee
- All evidence bundles can be regenerated via `scripts/phase6_final_reality_run.py`
- Runtime state is recreated automatically on fresh execution
- Phase 6 verification is fully reproducible from source
- Repository remains lean while preserving complete audit trail

## �🟢 CORE COMPONENTS (Included in Open-Core Release)

### Reliability Substrate
- ✅ **Timeout Enforcement**: Central timeout manager with deterministic audit codes
- ✅ **Retry Policy Framework**: Bounded retries with exponential backoff and idempotency
- ✅ **Backpressure & Rate Limiting**: Token bucket rate limiting with bounded queues
- ✅ **Circuit Breakers**: State machine protection for external dependencies
- ✅ **Audit & Observability**: Comprehensive audit trail and monitoring

### Safety & Governance
- ✅ **Kill Switches**: Emergency stop mechanisms
- ✅ **Tenant Isolation**: Multi-tenant resource isolation
- ✅ **Operator Approval**: Human-in-the-loop approval system
- ✅ **Authentication/Authorization**: Basic auth and permission system

### Core Infrastructure
- ✅ **NATS JetStream Integration**: Message streaming and persistence
- ✅ **Replay Engine**: Deterministic replay capabilities
- ✅ **Configuration Management**: Centralized configuration system
- ✅ **Golden Demo**: Reference implementation and tests

---

## 🟡 EXPERIMENTAL COMPONENTS (Future Development)

### Advanced Analytics
- ⚠️ **Machine Learning Integration**: ML-based anomaly detection
- ⚠️ **Advanced Metrics**: Performance analytics and dashboards
- ⚠️ **Predictive Scaling**: AI-driven resource optimization

### External Integrations
- ⚠️ **Third-party APIs**: External service integrations beyond core
- ⚠️ **Federated Learning**: Distributed learning capabilities
- ⚠️ **Cloud Provider Integrations**: Multi-cloud deployment tools

### Enhanced Features
- ⚠️ **Advanced UI**: Web-based management interface
- ⚠️ **Multi-region Deployment**: Geographic distribution
- ⚠️ **Advanced Security**: Enhanced security features

---

## 🔴 EXCLUDED COMPONENTS (Not Part of Core)

### Proprietary Extensions
- ❌ **Enterprise Features**: Commercial-only capabilities
- ❌ **Advanced Support**: Premium support tools
- ❌ **Professional Services**: Consulting add-ons

### Development Tools
- ❌ **Development Frameworks**: Internal dev tools
- ❌ **Testing Infrastructure**: Advanced testing frameworks
- ❌ **Build Systems**: Internal build and CI tools

---

## BOUNDARY DEFINITION

### What Defines "Core"
1. **Production-Ready**: Components required for production deployment
2. **Self-Contained**: No external dependencies beyond standard libraries
3. **Well-Documented**: Complete documentation and examples
4. **Fully Tested**: Comprehensive test coverage
5. **Stable API**: No breaking changes between versions

### What Defines "Experimental"
1. **Development Stage**: Still in development or beta
2. **External Dependencies**: Requires additional services or APIs
3. **Limited Documentation**: Documentation may be incomplete
4. **Changing API**: May have breaking changes
5. **Optional Features**: Not required for core functionality

### What Defines "Excluded"
1. **Internal Tools**: Tools for internal development only
2. **Commercial Features**: Revenue-generating capabilities
3. **Third-party IP**: Components with licensing restrictions
4. **Non-Essential**: Features not required for core functionality

---

## RELEASE COMPOSITION

### Open-Core Release Includes
```
src/
├── reliability/           # ✅ Core reliability substrate
├── auth/                 # ✅ Authentication and authorization
├── audit/                # ✅ Audit logging and observability
├── replay/               # ✅ Replay engine
├── nats_client.py        # ✅ NATS integration
└── core/                 # ✅ Core infrastructure

tests/
├── test_phase6_*.py      # ✅ Phase 6 reliability tests
├── test_gate5_*.py       # ✅ Phase 5 safety tests
└── golden_demo/          # ✅ Reference implementation

scripts/
├── phase6_final_reality_run.py  # ✅ Verification script
└── phase5_final.py             # ✅ Phase 5 verification

artifacts/
└── reality_run_008/      # ✅ Evidence bundle
```

### Experimental Components (Separate Repository)
```
experimental/
├── ml_integration/       # ⚠️ Machine learning features
├── advanced_analytics/   # ⚠️ Analytics dashboards
├── external_apis/       # ⚠️ Third-party integrations
└── cloud_deployment/    # ⚠️ Multi-cloud tools
```

---

## LICENSING IMPLICATIONS

### Core Components (Open Source)
- **License**: MIT/Apache 2.0 (permissive open source)
- **Usage**: Free to use, modify, and distribute
- **Support**: Community support only
- **Updates**: Regular updates with core improvements

### Experimental Components (Source Available)
- **License**: Source-available with restrictions
- **Usage**: Evaluation and development only
- **Support**: Best-effort community support
- **Updates**: May have breaking changes

### Excluded Components (Proprietary)
- **License**: Commercial license required
- **Usage**: Enterprise customers only
- **Support**: Professional support included
- **Updates**: Guaranteed updates and SLA

---

## MIGRATION PATH

### From Experimental to Core
1. **Stabilization**: API becomes stable and documented
2. **Testing**: Comprehensive test coverage achieved
3. **Dependencies**: All external dependencies resolved
4. **Community Review**: Community approval and feedback
5. **Formal Promotion**: Official promotion to core

### From Core to Experimental
1. **Deprecation Notice**: 6-month deprecation period
2. **Migration Path**: Clear migration to replacement
3. **Documentation**: Updated documentation
4. **Community Communication**: Clear communication about changes
5. **Final Removal**: Removal from core release

---

## VERIFICATION

### Core Component Verification
```bash
# Verify all core components are present and functional
python3 scripts/phase6_final_reality_run.py

# Expected: All gates GREEN, all tests PASS
```

### Boundary Compliance Check
```bash
# Verify no experimental components in core release
find src/ -name "*.py" | grep -v "__pycache__" | wc -l
# Expected: Only core components present

# Verify documentation completeness
ls docs/ | grep -E "(reliability|auth|audit|replay)"
# Expected: All core components documented
```

### Release Integrity Check
```bash
# Verify release bundle integrity
python3 -m tests.test_phase6_timeout_simple
python3 -m tests.test_phase6_retry_minimal
python3 -m tests.test_phase6_backpressure_minimal
python3 -m tests.test_phase6_circuit_breaker_minimal

# Expected: All tests pass without additional dependencies
```

---

## SUMMARY

The ExoArmur open-core release includes all components required for production-grade reliability and safety. Experimental features are clearly separated and labeled, with no ambiguity about what is included in the core release.

**Core Release**: Production-ready reliability substrate with comprehensive testing and documentation.  
**Experimental**: Future development features with clear labeling and separation.  
**Excluded**: Internal tools and commercial features not relevant to core functionality.
