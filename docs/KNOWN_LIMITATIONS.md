# Known Limitations

*Last updated: June 1, 2026*

## Overview

This document catalogues the known limitations of ExoArmur-Core as of the current version (2.1.0). These limitations are disclosed to enable informed evaluation and due diligence.

## Security & Certification Limitations

### No Third-Party Security Audit
- **Status**: Security and compliance are self-validated only
- **Impact**: No independent security review has been conducted
- **Mitigation**: Comprehensive internal security scanning (bandit, pip-audit, gitleaks) is enforced via CI
- **Path Forward**: Seeking third-party security audit partnership

### No Production Certification
- **Status**: Not certified for production use
- **Impact**: Cannot claim production readiness or compliance certifications
- **Mitigation**: Reference implementation status clearly documented
- **Path Forward**: Seeking formal verification partnership and pilot integrations

### DACT Level 6 Pending
- **Status**: Levels 1-5 internally validated, Level 6 pending third-party review
- **Impact**: Formal verification not yet completed
- **Mitigation**: Invariants tested via comprehensive test suite
- **Path Forward**: Formal verification requires theorem-prover output or formal specification proofs

## Implementation Limitations

### TrustEvaluator Interface-Only
- **Status**: TrustEvaluator raises NotImplementedError
- **Impact**: No real trust scoring logic implemented
- **Mitigation**: Formal interface defined for future implementation
- **Path Forward**: Requires implementation for production use with actual vendor scoring

### Platform Executors Are Scaffolds
- **Status**: LangChain, OpenAI, Anthropic, HuggingFace executors are reference implementations only
- **Impact**: No actual vendor SDK integrations or API calls
- **Mitigation**: Plugin infrastructure and evidence schema provided
- **Path Forward**: Production-ready integrations belong in optional addon packages

### Executor Contract Inconsistency
- **Status**: Some methods (get_state_hash, get_execution_history) not part of formal ExecutorPlugin protocol
- **Impact**: 17 test skips due to contract assumptions not matching implementation
- **Mitigation**: Known skip categories documented in test suite
- **Path Forward**: Executor contract formalization needed to decide protocol requirements

## Operational Limitations

### No Known Production Deployments
- **Status**: No real-world operational history
- **Impact**: No production-scale performance data or operational experience
- **Mitigation**: Comprehensive E2E test coverage (22 tests)
- **Path Forward**: Seeking pilot integrations in high-assurance environments

### No Production Monitoring Infrastructure
- **Status**: No SLOs, alerting, or observability infrastructure defined
- **Impact**: Cannot guarantee production operational readiness
- **Mitigation**: Health check CLI command available
- **Path Forward**: Production monitoring requires SLO definition and observability stack

### No Incident Response Procedures
- **Status**: No documented incident response runbooks
- **Impact**: No validated incident response procedures
- **Mitigation**: Security policy defines vulnerability reporting process
- **Path Forward**: Incident response procedures require operational experience

## Testing Limitations

### Test Skips (17 total)
- **Status**: 338 passed, 17 skipped, 0 failed
- **Impact**: Some functionality not fully tested due to contract inconsistencies
- **Mitigation**: All skip categories documented and justified
- **Path Forward**: Executor contract formalization will reduce skips

### No Red Team Exercises
- **Status**: Federation crypto and handshake state machine not exercised against external red team
- **Impact**: Adversarial testing not conducted
- **Mitigation**: FaultInjector framework exists for deterministic replay testing
- **Path Forward**: Red team exercises require external security partnership

### No Byzantine Fault Tolerance Testing
- **Status**: FaultInjector framework exists but not tested in real distributed settings
- **Impact**: BFT consensus not validated in production-like conditions
- **Mitigation**: Replay determinism verified under adversarial input corruption
- **Path Forward**: BFT testing requires distributed environment

## Documentation Limitations

### License Requires Legal Review
- **Status**: License language needs legal counsel review
- **Impact**: Cannot proceed with public release, commercial licensing, or acquisition without legal review
- **Mitigation**: Proprietary evaluation license appropriate for current status
- **Path Forward**: Legal review required before any public or commercial action

### No Production Deployment Guide
- **Status**: No operational runbooks or deployment documentation
- **Impact**: Production deployment guidance not available
- **Mitigation**: Installation and quickstart documentation provided
- **Path Forward**: Production deployment guide requires operational experience

## Dependency Limitations

### Dependency Security Responsibility
- **Status**: Third-party dependencies out of scope for direct security reporting
- **Impact**: Vulnerabilities in dependencies must be reported to vendors
- **Mitigation**: pip-audit scans for known vulnerabilities on every push
- **Path Forward**: Dependency monitoring requires ongoing maintenance

### Python Version Support
- **Status**: Minimum supported Python version is 3.10
- **Impact**: Cannot run on Python < 3.10
- **Mitigation**: Tested across Python 3.10, 3.11, 3.12
- **Path Forward**: Older Python support not planned

## Architectural Limitations

### No Built-in Persistence
- **Status**: Core does not include built-in audit storage
- **Impact**: Audit persistence requires external storage integration
- **Mitigation**: Evidence schema provided for external storage
- **Path Forward**: Optional persistence modules can be added via plugin system

### No Built-in Federation
- **Status**: Federation crypto and handshake state machine not production-hardened
- **Impact**: Multi-node federation not production-ready
- **Mitigation**: Federation framework exists but not battle-tested
- **Path Forward**: Federation requires external red team exercises and pilot deployments

### No Built-in Authentication/Authorization
- **Status**: No built-in authn/z system
- **Impact**: Access control must be implemented externally
- **Mitigation**: Governance boundary enforces policy gates regardless of authn/z
- **Path Forward**: Authn/z integration requires external identity provider

## Summary

ExoArmur-Core is a **reference implementation** with comprehensive internal validation but lacks third-party certification, production operational experience, and some production-ready implementations. These limitations are disclosed to enable informed evaluation.

The system is **ready for private NDA buyer review** and **IP-only sale diligence** but **not ready for public release** or **enterprise production deployment** without addressing the limitations above.

## Current Status

- **Version**: 2.1.0
- **License**: Proprietary evaluation license
- **Stage**: Private reference implementation, buyer/pilot evaluation ready
- **Last updated**: June 1, 2026
