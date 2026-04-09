# ExoArmur Open-Core Boundary Definition

**Versioning**

- Architecture / Contract: v1.0.0 (stable)
- Package (pip): 2.0.0

## 🚨 RUNTIME & ARTIFACTS POLICY

### Repository Hygiene
- **data/**: NATS JetStream runtime state - generated locally, excluded from Git
- **artifacts/reality_run_**/**: Evidence bundles - reproducible, not stored in Git  
- **__pycache__/**, *.pyc: Python bytecode - excluded from Git
- **.venv/**: Virtual environments - excluded from Git
- **logs/**: Runtime logs - excluded from Git

### Evidence Bundle Policy
- No reality_run evidence bundles are committed to Git
- Evidence is regenerated deterministically via `scripts/phase6_final_reality_run.py`
- Repository may contain only empty placeholder directories or documentation examples outside runtime paths
- All evidence bundles are reproducible from source code

### Reproducibility Guarantee
- All evidence bundles can be regenerated via `scripts/phase6_final_reality_run.py`
- Runtime state is recreated automatically on fresh execution
- Phase 6 reality run is fully reproducible from source
- Repository remains lean while preserving complete audit trail

## 🟢 CORE COMPONENTS (Included in Open-Core Release)

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

### Truth Enforcement
- ✅ **Tests**: All verification scripts and test suites
- ✅ **Reality Runs**: Phase 6 reality run and gate verification
- ✅ **Golden Demo Enforcement**: Reference implementation validation
- ✅ **Audit Trail**: Complete deterministic replay capability

---

## 🔴 EXCLUDED COMPONENTS (Not Part of Core)

### Proprietary Extensions
- ❌ **Enterprise Features**: Commercial-only capabilities
- ❌ **Advanced Support**: Premium support tools
- ❌ **Professional Services**: Consulting add-ons

### Internal Development Infrastructure
- ❌ **CI/CD Pipelines**: Organization-specific automation
- ❌ **Build Systems**: Internal build and deployment tools
- ❌ **Secrets Management**: Organizational credential systems
- ❌ **Monitoring Infrastructure**: Internal observability stacks

---

## BOUNDARY DEFINITION

### What Defines "Core"
1. **Production-Ready**: Components required for production deployment
2. **OSS Dependencies**: Uses open-source Python dependencies declared in requirements files
3. **Runtime Requirements**: Requires NATS JetStream for Golden Demo and Phase 6 reality run
4. **No Proprietary Dependencies**: No paid or commercial dependencies in core
5. **Numerical / data-science libraries (numpy, pandas, scipy) are prohibited in core to preserve deterministic minimal-runtime guarantees**
6. **Well-Documented**: Complete documentation and examples
7. **Fully Tested**: Comprehensive test coverage
8. **Stable API**: No breaking changes between versions
9. **Truth Enforcement**: Contains all verification and testing infrastructure

### What Defines "Excluded"
1. **Internal Tools**: Tools for internal development only
2. **Commercial Features**: Revenue-generating capabilities
3. **Third-party IP**: Components with licensing restrictions
4. **Non-Essential**: Features not required for core functionality
5. **Organizational Infrastructure**: CI/CD, secrets, internal systems

### Experimental Repository Boundary
- Experimental components do NOT exist inside the core repository
- Experimental work lives in a separate repository, branch, or explicitly gated distribution
- The core repo contains only production-truth components
- No experimental code directories exist in core repository structure

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
├── test_*.py            # ✅ All verification tests
└── golden_demo/          # ✅ Reference implementation

examples/
├── demo_standalone.py           # ✅ Canonical standalone deny/proof demo
├── demo_standalone_proof_bundle.json  # ✅ Deterministic proof artifact
└── quickstart_replay.py         # ✅ Infra-free replay quickstart

scripts/
├── phase6_final_reality_run.py  # ✅ Phase 6 reality run
├── phase5_final.py             # ✅ Phase 5 verification
└── *.py                       # ✅ All utility scripts

docs/
├── *.md                   # ✅ All documentation
└── assets/               # ✅ Documentation assets

requirements.txt            # ✅ OSS Python dependencies
docker-compose.yml          # ✅ Runtime definition
```

### Explicitly Excluded
```
artifacts/reality_run_*/    # ❌ No evidence bundles in Git
data/                      # ❌ No runtime state in Git
.venv*/                    # ❌ No virtual environments
__pycache__/               # ❌ No Python bytecode
logs/                      # ❌ No runtime logs
```

---

## DEPENDENCY TRUTH

### External Dependencies
- **Core uses OSS Python dependencies** declared in requirements files
- **Runtime requires NATS JetStream** to satisfy Golden Demo and Phase 6 reality run
- **No proprietary or paid dependencies** exist in core
- **All dependencies are open-source** with permissive licensing

### Runtime Requirements
- **NATS JetStream Server**: Required for message persistence and streaming
- **Docker/Docker Compose**: Required for containerized deployment
- **Python 3.8+**: Required runtime environment
- **OSS Libraries**: All listed in requirements.txt

---

## LICENSING IMPLICATIONS

### Core Components (Open Source)
- **License**: Apache 2.0 (permissive open source)
- **Usage**: Free to use, modify, and distribute
- **Support**: Community support only
- **Updates**: Regular updates with core improvements
- **Dependencies**: All open-source, no commercial requirements

---

## VERIFICATION

### Core Component Verification
```bash
# Verify all core components are present and functional
python3 examples/demo_standalone.py

# Expected: Denial markers and proof bundle are produced deterministically
```

### Boundary Compliance Check
```bash
# Verify no experimental components in core release
find src/ -name "*.py" | grep -v "__pycache__" | wc -l
# Expected: Only core components present

# Verify no evidence bundles in Git
git ls-files | grep "artifacts/reality_run_"
# Expected: No output (no tracked evidence bundles)

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

The ExoArmur open-core release includes all components required for production-grade reliability and safety. The repository contains only production-truth components with comprehensive verification and testing infrastructure.

**Core Release**: Production-ready reliability substrate with comprehensive testing, documentation, and truth enforcement.  
**Dependencies**: Open-source Python dependencies with NATS JetStream runtime requirement.  
**Excluded**: Internal tools, commercial features, and organizational infrastructure not relevant to core functionality.  
**Boundary**: Mechanically enforceable with no experimental code in core repository.