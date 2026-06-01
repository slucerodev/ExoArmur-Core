# Technical Diligence

*Prepared for: Prospective Acquirers and Strategic Buyers*
*Date: June 1, 2026*
*Version: 2.1.0*

## Architecture Overview

### Core Components

**Kernel (~1,680 lines):**
- `kernel/boundary.py` - ProxyPipeline execution boundary (Intent → Policy → Safety → Executor → Audit)
- `kernel/clock.py` - Clock abstraction with utc_now and DeterministicClock
- `kernel/ids.py` - Deterministic ULID generation for governance entities
- `kernel/trust_evaluator.py` - Formal interface (raises NotImplementedError)
- `kernel/external_effect.py` - External effect evidence and replay verification
- `kernel/replay_verification.py` - Replay verification engine
- `kernel/plugin_registry.py` - Plugin discovery and registration
- `kernel/canonicalization.py` - Canonical JSON encoding

**Core Executors:**
- `executors/file_system_executor.py` - FileSystemExecutor with governance integration
- `executors/database_executor.py` - DatabaseExecutor with transaction rollback

**Platform Executor Scaffolds:**
- `executors/langchain_executor.py` - LangChainExecutor scaffold
- `executors/openai_executor.py` - OpenAIExecutor scaffold
- `executors/anthropic_executor.py` - AnthropicExecutor scaffold
- `executors/huggingface_executor.py` - HuggingFaceExecutor scaffold

### Design Principles

1. **Determinism** - All governance decisions are deterministic and replayable
2. **Minimalism** - Small codebase for auditability and maintainability
3. **Separation of Concerns** - Clear boundary between governance and execution
4. **Plugin Architecture** - Extensible executor system via entry points
5. **Contract Immutability** - V1 contracts are locked and cannot be modified

## Code Quality Metrics

### Test Coverage
- **Unit tests**: 338 passed, 17 skipped, 0 failed
- **E2E tests**: 22 passed, 0 failed
- **Total test files**: 30+ test modules
- **Coverage areas**: Kernel, executors, integration, compliance, security, performance

### Code Quality Tools
- **Black**: All files compliant (45 files)
- **Isort**: All imports compliant
- **Mypy**: No errors (informational notes only for untyped functions)
- **Suppressions**: 6 type: ignore, 15 nosec (all narrow and justified)

### Security Scanning
- **Bandit SAST**: No issues identified (10 B608 properly suppressed with justification)
- **pip-audit**: No known vulnerabilities in Core dependencies (with upgraded pip 26.1.2)
- **Gitleaks**: No secrets in working tree
- **pip check**: No broken requirements

## Dependency Analysis

### Core Dependencies
- **pydantic** 2.12.5 - Data validation and parsing
- **cryptography** 48.0.0 - Cryptographic operations
- **python-ulid** 3.1.0 - Deterministic ID generation
- **click** 8.4.1 - CLI framework
- **python-json-logger** 4.1.0 - Structured logging
- **typing-extensions** 4.15.0 - Type hints
- **typing-inspection** 0.4.2 - Type inspection
- **cffi** 2.0.0 - Foreign function interface (cryptography dependency)
- **annotated-types** 0.7.0 - Type annotations (pydantic dependency)

### Dependency Security
All dependencies scanned with pip-audit using upgraded pip (26.1.2) in fresh virtual environment. Zero known vulnerabilities found.

### Dependency Licensing
All dependencies use permissive licenses compatible with commercial use:
- pydantic: MIT
- cryptography: Apache 2.0 / BSD
- python-ulid: MIT
- click: BSD
- python-json-logger: BSD
- typing-extensions: MIT
- typing-inspection: MIT
- cffi: MIT
- annotated-types: MIT

See `THIRD_PARTY_NOTICES.md` for complete attribution.

## Security Architecture

### Threat Model
ExoArmur addresses four primary threat classes:
1. **Policy evasion** - Direct executor invocation, intent mutation, race conditions
2. **Audit tampering** - Deletion, modification, or injection of audit records
3. **Safety override** - Bypassing safety gate decisions
4. **Executor compromise** - Malicious or sandbox-escaping executor modules

### Defenses
- **ProxyPipeline execution boundary** - Single governance boundary
- **Read-only ActionIntent** - Governance path cannot mutate intent
- **Deterministic policy evaluation** - Reproducible decisions
- **Untrusted executor model** - Executors treated as capability modules
- **Tamper-evident audit records** - Cryptographic integrity verification

### Security Limitations
- No third-party security audit (self-validated only)
- No built-in authentication/authorization
- No built-in persistence (requires external storage)
- TrustEvaluator is interface-only (no real scoring logic)

## Performance Characteristics

### Determinism Guarantees
- **Canonical JSON** - Sorted keys, no whitespace variation
- **Controlled clock** - Deterministic time for replay, wall-clock for coordination
- **Zero randomness** - No random decisions in governance path
- **Zero ML in authority path** - No ML in policy or safety evaluation

### Performance Metrics
- **Test execution time**: ~5.3 seconds for full test suite
- **E2E test execution time**: ~0.3 seconds
- **Memory footprint**: Minimal (pure Python, no heavy dependencies)
- **Startup time**: Sub-second for CLI commands

### Scalability Considerations
- **Single-node operation** - No built-in federation or distribution
- **Audit storage** - Requires external storage for production use
- **Plugin overhead** - Minimal plugin discovery and loading overhead

## Extensibility

### Plugin System
- **Entry points** - Standard Python entry points for plugin discovery
- **Executor interface** - Well-defined ExecutorPlugin protocol
- **Feature flags** - Optional capabilities gated behind explicit controls
- **Contract extensibility** - Additive-only changes to V1 contracts

### Extension Points
- Custom executors via plugin system
- Custom policy evaluators
- Custom safety evaluators
- Custom audit storage backends
- Custom trust evaluators

### Integration Examples
- FileSystemExecutor and DatabaseExecutor demonstrate full integration
- Platform executor scaffolds show integration patterns
- Plugin registry shows discovery mechanism

## Compliance Status

### DACT Compliance (v0.2)
| Level | Requirement | Status | Evidence |
|-------|-------------|--------|----------|
| 1 | Deterministic Replay | ✅ Internally validated | Test suite |
| 2 | Cryptographic Attestation | ✅ Internally validated | Test suite |
| 3 | Counterfactual Analysis | ✅ Internally validated | Test suite |
| 4 | ML Isolation | ✅ Internally validated | Test suite |
| 5 | Air-Gap Integrity | ✅ Internally validated | Test suite |
| 6 | Formal Verification | ⏳ Pending | Third-party review |

### Regulatory Considerations
- **No compliance certifications** - Not SOC 2, ISO 27001, or similar certified
- **Audit trail capabilities** - Cryptographic audit trails support compliance requirements
- **Data locality** - Air-gapped operation supports data sovereignty requirements

## Operational Readiness

### Current State
- **Development environment** - Designed for development and evaluation
- **No production deployments** - No known production operational experience
- **No monitoring infrastructure** - No SLOs, alerting, or observability defined
- **No incident response** - No documented incident response procedures

### Production Requirements
To operate in production, the following would need to be added:
- TrustEvaluator implementation
- Production monitoring and observability
- Incident response procedures
- Audit storage backend
- Authentication/authorization system
- Deployment automation
- Operational runbooks

## Technical Risks

### High Priority
1. **No third-party security audit** - Security claims are self-validated only
2. **TrustEvaluator not implemented** - Requires implementation for production use
3. **No production operational experience** - Unknown performance at scale

### Medium Priority
1. **Platform executors are scaffolds** - Require implementation for real vendor integrations
2. **Executor contract inconsistencies** - 17 test skips due to contract assumptions
3. **No built-in persistence** - Requires external storage integration

### Low Priority
1. **No built-in authentication** - Can be added externally
2. **No built-in monitoring** - Can be added externally
3. **License requires legal review** - Standard for proprietary software

## Technical Debt

### Known Issues
- 17 test skips due to executor contract inconsistencies
- TrustEvaluator raises NotImplementedError
- Platform executors are scaffolds only
- Some code uses type: ignore for dynamic plugin loading

### Refactoring Opportunities
- Executor contract formalization to reduce test skips
- TrustEvaluator implementation
- Platform executor production implementations
- Enhanced type coverage for dynamic plugin loading

## Documentation Quality

### Available Documentation
- Architecture documentation
- DACT Standard specification
- Security policy and threat model
- API documentation
- Integration guides
- Validation matrix
- Known limitations disclosure

### Documentation Gaps
- No production deployment guide
- No operational runbooks
- No performance tuning guide
- No troubleshooting guide

## Conclusion

ExoArmur-Core demonstrates high code quality, comprehensive test coverage, and clean security scan results. The architecture is well-designed for determinism and auditability. However, the system lacks third-party security audit, production operational experience, and some production-certified implementations. Note: This is a reference implementation with no third-party security audit, not production-certified.

For acquisition evaluation, the technical foundation is solid but requires investment in security audit, production hardening, and implementation of placeholder components before production deployment.
