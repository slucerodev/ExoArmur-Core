# Buyer Memo

*Prepared for: Prospective Acquirers and Strategic Buyers*
*Date: June 1, 2026*
*Version: 2.1.0*

## Executive Summary

ExoArmur-Core is a minimal deterministic governance kernel for autonomous systems. The software enforces policy gates, produces cryptographic audit trails, and enables deterministic replay verification. This memo provides a high-level overview for acquisition evaluation.

## What ExoArmur Is

A deterministic governance runtime that sits between an AI decision layer and execution targets. Every action passes through a policy gate, produces a cryptographic audit trail, and is deterministically replayable.

**Key Value Propositions:**
- Deterministic governance for autonomous systems
- Cryptographic audit trails with tamper evidence
- Replay verification for accountability
- Plugin-capable executor architecture
- Zero network dependencies in Core runtime
- Air-gapped operation capability

## What ExoArmur Is Not

- **Not** a full autonomous system — it is a governance layer, not an agent
- **Not** a platform executor — Core does not include vendor SDK integrations
- **Not** production-certified — this is a reference implementation seeking formal verification
- **Not** externally audited — security and compliance are self-validated
- **Not** a web service — the kernel is importable as a pure Python library

## Current Status

**Development Stage:** Private reference implementation, buyer/pilot evaluation ready

**Version:** 2.1.0

**License:** Proprietary evaluation license (requires written agreement for commercial use)

**Validation Status:**
- Test suite: 338 passed, 17 skipped, 0 failed
- E2E tests: 22 passed, 0 failed
- Code quality: black/isort/mypy clean
- Security scanning: Bandit clean, pip-audit clean (with upgraded pip)
- DACT compliance: Levels 1-5 internally validated, Level 6 pending

## Technical Overview

**Architecture:** ~1,680 lines of kernel code organized into:
- ProxyPipeline execution boundary
- Deterministic clock abstraction
- Cryptographic audit trail generation
- Replay verification engine
- Plugin registry for extensible executors
- Canonical JSON encoding for determinism

**Core Executors:**
- FileSystemExecutor — governs file operations with rollback
- DatabaseExecutor — governs database operations with transaction rollback

**Platform Executor Scaffolds:**
- LangChain, OpenAI, Anthropic, HuggingFace executors (reference implementations only)

## IP Assets

**Source Code:** Complete Python codebase with comprehensive test coverage

**Documentation:**
- Architecture documentation
- DACT Standard v0.2 specification
- Security policy and threat model
- API documentation
- Integration guides

**Contracts:** Immutable V1 data shapes in `spec/contracts/`

**Demo Artifacts:** Safe public sample data for demonstration

## Market Position

**Target Markets:**
- Defense and sovereign infrastructure
- Critical systems requiring high assurance
- Regulated industries requiring audit trails
- AI safety and governance research

**Competitive Differentiation:**
- Deterministic replay verification
- Cryptographic audit trails
- Air-gapped operation capability
- Minimal codebase for auditability
- Plugin architecture for extensibility

## Known Limitations

**Security & Certification:**
- No third-party security audit (self-validated only)
- Not production-certified
- DACT Level 6 pending formal verification

**Implementation:**
- TrustEvaluator is interface-only (raises NotImplementedError)
- Platform executors are scaffolds (no actual vendor integrations)
- Executor contract inconsistencies (17 test skips)

**Operational:**
- No known production deployments
- No production monitoring infrastructure
- No incident response procedures

**Documentation:**
- License requires legal review before public/commercial use
- No production deployment guide

See `docs/KNOWN_LIMITATIONS.md` for complete limitations disclosure.

## Acquisition Considerations

**Strengths:**
- High code quality with comprehensive test coverage
- Clean security scan results
- Well-documented architecture and limitations
- Minimal codebase for maintainability
- Plugin architecture for extensibility
- Clear separation of Core vs optional components

**Risks:**
- No third-party security audit
- No production operational experience
- Some components require implementation for production use
- License requires legal review
- No known customers or revenue

**Integration Requirements:**
- TrustEvaluator implementation for real trust scoring
- Platform executor production implementations for vendor integrations
- Production monitoring and observability infrastructure
- Incident response procedures
- Legal review of license terms

## Due diligence Materials

**Technical:**
- `docs/VALIDATION_MATRIX.md` - Complete validation status
- `docs/KNOWN_LIMITATIONS.md` - Known limitations disclosure
- `docs/acquisition/TECHNICAL_DILIGENCE.md` - Technical deep-dive
- `docs/acquisition/IP_ASSET_INVENTORY.md` - IP asset catalog
- `docs/DEPENDENCY_REVIEW.md` - Dependency analysis

**Commercial:**
- `docs/acquisition/BUY_VS_BUILD.md` - Build vs buy analysis
- `docs/acquisition/BUYER_FAQ.md` - Frequently asked questions
- `docs/acquisition/DILIGENCE_CHECKLIST.md` - Due diligence checklist

**Operational:**
- `docs/acquisition/DEMO_SCRIPT.md` - Demonstration script
- `docs/security/SECURITY_AUDIT_RECEIPT.md` - Security audit status
- `THIRD_PARTY_NOTICES.md` - Third-party license attributions

## Next Steps

1. Review technical documentation and validation matrix
2. Evaluate alignment with strategic objectives
3. Assess integration requirements and resource needs
4. Review legal and licensing considerations
5. Request demonstration or pilot evaluation

## Contact

For acquisition discussions, technical review, or pilot evaluation requests, contact the repository owner via GitHub.

## Disclaimer

This memo is provided for informational purposes only. No warranties or representations are made regarding the accuracy, completeness, or suitability of this information for any particular purpose. Acquisition decisions should be based on comprehensive due diligence and independent technical review.
