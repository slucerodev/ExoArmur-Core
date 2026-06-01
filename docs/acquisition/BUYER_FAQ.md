# Buyer FAQ

*Prepared for: Prospective Acquirers and Strategic Buyers*
*Date: June 1, 2026*
*Version: 2.1.0*

## General Questions

### What is ExoArmur-Core?

ExoArmur-Core is a minimal deterministic governance kernel for autonomous systems. It enforces policy gates, produces cryptographic audit trails, and enables deterministic replay verification. It sits between an AI decision layer and execution targets to provide governance and accountability.

### What stage of development is ExoArmur-Core in?

ExoArmur-Core is a private reference implementation at version 2.1.0, ready for buyer/pilot evaluation under NDA. It is not production-certified and has not undergone third-party security audit.

### What does "reference implementation" mean?

Reference implementation means the system demonstrates the architecture and concepts but is not yet hardened for production deployment. It has comprehensive internal validation but lacks third-party certification and production operational experience.

### Can I use ExoArmur-Core in production today?

No. ExoArmur-Core is not production-certified and lacks third-party security audit. It is ready for private NDA evaluation and pilot testing, but production deployment requires additional work including third-party security audit, production monitoring infrastructure, and implementation of placeholder components.

## Technical Questions

### What programming language is ExoArmur-Core written in?

ExoArmur-Core is written in Python 3.10+. It is a pure Python library with zero network dependencies in the Core runtime.

### What are the system requirements?

- Python 3.10 or later
- Linux, macOS, or Windows
- ~50MB disk space for installation
- Minimal memory footprint (pure Python)

### How big is the codebase?

The Core kernel is approximately 1,680 lines of code. The total source code (excluding tests and documentation) is approximately 5,453 lines.

### What is the test coverage?

The test suite has 338 tests passing, 17 skipped, 0 failed. E2E tests have 22 tests passing, 0 failed.

### What dependencies does ExoArmur-Core have?

Core dependencies include pydantic, cryptography, python-ulid, click, python-json-logger, and typing-extensions. All dependencies use permissive licenses (MIT, BSD, Apache 2.0). See `docs/DEPENDENCY_REVIEW.md` for complete analysis.

### Does ExoArmur-Core require network access?

No. The Core runtime has zero network dependencies. It can operate in air-gapped environments.

### Can ExoArmur-Core be deployed in air-gapped environments?

Yes. ExoArmur-Core is designed for air-gapped operation and has been validated for DACT Level 5 (Air-Gap Integrity).

### What is the plugin architecture?

ExoArmur-Core uses Python entry points for plugin discovery. Executors and other extensions can be added as separate packages that are discovered at runtime via the plugin registry.

### What executors are included?

Core includes FileSystemExecutor and DatabaseExecutor (internally validated). Platform executor scaffolds for LangChain, OpenAI, Anthropic, and HuggingFace are included as reference implementations only.

### Why are platform executors scaffolds?

Platform executors are scaffolds because they don't include actual vendor SDK integrations or API calls. They demonstrate the integration pattern but require implementation for production use. Real platform integrations belong in optional addon packages.

## Security Questions

### Has ExoArmur-Core undergone third-party security audit?

No. Security and compliance are self-validated only using internal tools (bandit, pip-audit, gitleaks).

### What security scanning is performed?

ExoArmur-Core uses automated security scanning on all changes:
- Bandit SAST for Python code
- pip-audit for dependency vulnerabilities
- Gitleaks for secret detection

### Are there any known security vulnerabilities?

No. The current default Core install shows zero known vulnerabilities when scanned with pip-audit using upgraded pip (26.1.2) in a fresh virtual environment.

### What is the threat model?

ExoArmur addresses four primary threat classes: policy evasion, audit tampering, safety override, and executor compromise. See `SECURITY.md` for detailed threat model.

### Does ExoArmur-Core include authentication/authorization?

No. Authentication and authorization must be implemented externally. ExoArmur enforces policy gates regardless of authn/z.

### Does ExoArmur-Core include audit storage?

No. Audit storage requires external integration. ExoArmur provides the evidence schema for external storage backends.

## Integration Questions

### How long does it take to integrate ExoArmur-Core?

Basic integration can be done in 3-6 months. Full production deployment with custom executors, monitoring, and third-party security audit may take 12-18 months.

### What components need to be implemented for production?

For production deployment, you would need to implement:
- TrustEvaluator (currently interface-only)
- Platform executor production implementations (if vendor integrations needed)
- Production monitoring and observability infrastructure
- Audit storage backend
- Authentication/authorization system
- Incident response procedures

### Can I customize the policy evaluation?

Yes. The policy evaluation system is designed to be customizable. You can implement custom policy evaluators via the plugin architecture.

### Can I add custom executors?

Yes. Custom executors can be added via the plugin architecture using Python entry points.

### Does ExoArmur-Core support my specific use case?

ExoArmur-Core is designed for deterministic governance of autonomous systems. It is particularly well-suited for high-assurance environments (defense, sovereign infrastructure, critical systems). Contact the repository owner to discuss your specific use case.

## Licensing Questions

### What is the current license?

ExoArmur-Core is under a proprietary evaluation license. Evaluation access does not grant production use rights.

### Can I use ExoArmur-Core for evaluation under NDA?

Yes. ExoArmur-Core is ready for private NDA buyer review and pilot evaluation.

### What are the terms for commercial use?

Commercial use requires a separate written agreement. Contact the repository owner for licensing discussions.

### Does the license require legal review?

Yes. License language should be reviewed by legal counsel before public release, commercial licensing, or acquisition.

### Are third-party licenses compatible with commercial use?

Yes. All third-party dependencies use permissive licenses (MIT, BSD, Apache 2.0) compatible with commercial use. See `THIRD_PARTY_NOTICES.md` for complete attribution.

## Acquisition Questions

### What is included in the acquisition package?

The acquisition package includes:
- Complete source code (~5,453 lines)
- Comprehensive test suite (338 tests)
- Complete documentation
- CI/CD infrastructure
- Demo artifacts
- V1 contracts (immutable)
- All IP assets as cataloged in `docs/acquisition/IP_ASSET_INVENTORY.md`

### What is NOT included?

The following are NOT included:
- Third-party dependencies (managed via pip)
- External audit reports (none conducted)
- Production deployment infrastructure (none exists)
- Customer data (none exists)
- Operational runbooks (none exists)
- Incident response procedures (none exists)

### What is the recommended acquisition price?

See `docs/acquisition/BUY_VS_BUILD.md` for detailed cost analysis. The break-even analysis suggests acquisition is economically superior to building from scratch at or below $2.7M over a 3-year horizon.

### What are the post-acquisition integration costs?

Estimated integration costs are $450k - $900k for:
- TrustEvaluator implementation
- Platform executor implementations
- Production monitoring infrastructure
- Legal review of license

### What are the ongoing maintenance costs?

Estimated ongoing maintenance costs are $150k - $300k/year for:
- Maintenance and updates
- Security updates
- Support

## Due Diligence Questions

### What due diligence materials are available?

See `docs/acquisition/DILIGENCE_CHECKLIST.md` for a complete due diligence checklist. Available materials include:
- Validation matrix
- Known limitations disclosure
- Technical deep-dive
- IP asset inventory
- Build vs buy analysis
- Demo script
- Dependency review
- Security audit receipt

### How do I verify the test results?

Run the validation commands in `docs/VALIDATION_MATRIX.md` to reproduce the test results locally.

### How do I verify the security scan results?

Run the security scanning commands in `docs/VALIDATION_MATRIX.md` to reproduce the security scan results locally.

### Can I request a demonstration?

Yes. Contact the repository owner to request a demonstration or pilot evaluation.

### Can I request a pilot integration?

Yes. ExoArmur-Core is seeking first integration in high-assurance environments. Contact the repository owner for pilot evaluation discussions.

## Limitations Questions

### What are the known limitations?

See `docs/KNOWN_LIMITATIONS.md` for complete limitations disclosure. Key limitations include:
- No third-party security audit
- Not production-certified
- TrustEvaluator is interface-only
- Platform executors are scaffolds
- No known production deployments
- No production monitoring infrastructure

### Are these limitations blockers?

For private NDA evaluation and IP-only sale diligence, these limitations are not blockers. For production deployment, these limitations must be addressed.

### What is the path to production readiness?

The path to production readiness includes:
- Third-party security audit
- Production certification
- TrustEvaluator implementation
- Platform executor implementations
- Production monitoring infrastructure
- Incident response procedures
- Formal verification for DACT Level 6

## Support Questions

### What support is available?

Support is available via GitHub issues for technical review, architecture feedback, and formal verification collaboration. Production support requires separate agreement.

### What is the response time for security issues?

Security issues are acknowledged within 48-72 hours, triaged within 3-5 business days. See `SECURITY.md` for detailed response timeline.

### How are updates handled?

Updates are managed via semantic versioning. V1 contracts are immutable. New capabilities are additive and feature-flag gated.

### Can I get custom development?

Custom development can be discussed as part of acquisition or partnership agreements. Contact the repository owner for details.

## Contact

### Who do I contact for acquisition discussions?

Contact the repository owner via GitHub for acquisition, licensing, pilot, partnership, or acquisition discussions.

### How do I report security issues?

Open a private GitHub Security Advisory or contact the repository maintainer via GitHub. Do not open public issues for suspected security vulnerabilities.

### Where can I find more information?

See the documentation index in `README.md` for complete documentation including architecture, security policy, and integration guides.
