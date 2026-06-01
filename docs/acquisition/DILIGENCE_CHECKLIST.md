# Due Diligence Checklist

*Prepared for: Prospective Acquirers and Strategic Buyers*
*Date: June 1, 2026*
*Version: 2.1.0*

## Overview

This checklist provides a comprehensive due diligence framework for evaluating ExoArmur-Core for acquisition.

## Phase 1: Initial Screening

### Business Fit
- [ ] Aligns with strategic objectives for autonomous systems governance
- [ ] Fits target market (defense, sovereign infrastructure, critical systems)
- [ ] Complements existing technology stack
- [ ] Addresses clear business need (auditability, compliance, safety)

### Technical Fit
- [ ] Python 3.10+ compatibility with existing infrastructure
- [ ] Integration requirements understood and feasible
- [ ] Resource requirements (CPU, memory, storage) acceptable
- [ ] Deployment model compatible with operations

### Budget Fit
- [ ] Acquisition price within budget (see BUY_VS_BUILD.md for analysis)
- [ ] Integration costs ($450k - $900k) acceptable
- [ ] Ongoing maintenance costs ($150k - $300k/year) acceptable
- [ ] ROI analysis favorable vs build-from-scratch

## Phase 2: Technical Due Diligence

### Code Quality Review
- [ ] Review source code structure and organization
- [ ] Verify code quality metrics (black/isort/mypy clean)
- [ ] Review test coverage (338 tests, 22 E2E tests)
- [ ] Verify CI/CD infrastructure quality
- [ ] Review code suppressions (6 type: ignore, 15 nosec - all justified)

### Security Review
- [ ] Review security scanning results (bandit, pip-audit, gitleaks)
- [ ] Verify zero known vulnerabilities in dependencies
- [ ] Review threat model (SECURITY.md)
- [ ] Assess security architecture (ProxyPipeline, untrusted executor model)
- [ ] Evaluate need for third-party security audit

### Architecture Review
- [ ] Review kernel architecture (~1,680 lines)
- [ ] Review executor architecture (Core + scaffolds)
- [ ] Review plugin architecture and entry points
- [ ] Review determinism guarantees (canonical JSON, controlled clock)
- [ ] Review replay verification engine

### Dependency Review
- [ ] Review all dependencies (see DEPENDENCY_REVIEW.md)
- [ ] Verify all licenses are permissive (MIT, BSD, Apache 2.0)
- [ ] Assess dependency maintenance burden
- [ ] Review dependency security posture
- [ ] Verify no GPL or copyleft licenses

### Performance Review
- [ ] Review performance characteristics
- [ ] Assess scalability limitations
- [ ] Review test execution times
- [ ] Evaluate memory footprint
- [ ] Assess production performance requirements

## Phase 3: IP Due Diligence

### IP Ownership Verification
- [ ] Verify source code ownership
- [ ] Verify documentation ownership
- [ ] Verify test asset ownership
- [ ] Verify configuration file ownership
- [ ] Review any third-party code attributions

### IP Asset Inventory
- [ ] Review complete IP asset inventory (IP_ASSET_INVENTORY.md)
- [ ] Verify all assets are included in acquisition package
- [ ] Identify any excluded assets
- [ ] Review V1 contracts (immutable)
- [ ] Review demo artifacts (safe public data)

### License Review
- [ ] Review current license terms (LICENSE)
- [ ] Conduct legal review of license language
- [ ] Verify third-party license compatibility
- [ ] Review THIRD_PARTY_NOTICES.md
- [ ] Assess license conversion requirements

### Patent Review
- [ ] Conduct patent search for ExoArmur-related patents
- [ ] Review any patent applications
- [ ] Assess patent infringement risk
- [ ] Evaluate freedom to operate
- [ ] Review IP assignment requirements

## Phase 4: Operational Due Diligence

### Production Readiness Assessment
- [ ] Review known limitations (KNOWN_LIMITATIONS.md)
- [ ] Assess production deployment requirements
- [ ] Identify required implementations (TrustEvaluator, platform executors)
- [ ] Assess monitoring infrastructure requirements
- [ ] Review incident response procedure requirements

### Integration Planning
- [ ] Identify integration points with existing systems
- [ ] Assess integration complexity
- [ ] Estimate integration timeline (3-6 months baseline)
- [ ] Identify required custom development
- [ ] Assess integration resource requirements

### Support and Maintenance
- [ ] Review current support model
- [ ] Assess ongoing maintenance burden
- [ ] Identify required support resources
- [ ] Review update and patch process
- [ ] Assess long-term support requirements

### Staffing Requirements
- [ ] Identify required engineering resources
- [ ] Identify required QA resources
- [ ] Identify required DevOps resources
- [ ] Assess training requirements
- [ ] Evaluate hiring needs

## Phase 5: Commercial Due Diligence

### Market Analysis
- [ ] Review target market size and growth
- [ ] Assess competitive landscape
- [ ] Evaluate differentiation vs competitors
- [ ] Review customer references (if any)
- [ ] Assess market timing

### Financial Analysis
- [ ] Review acquisition pricing rationale
- [ ] Compare build vs buy costs (BUY_VS_BUILD.md)
- [ ] Assess ROI over 3-5 year horizon
- [ ] Review total cost of ownership
- [ ] Evaluate break-even analysis

### Contract Review
- [ ] Review acquisition agreement terms
- [ ] Review IP assignment provisions
- [ ] Review warranty and indemnification
- [ ] Review non-compete provisions
- [ ] Review post-acquisition support terms

### Risk Assessment
- [ ] Identify technical risks
- [ ] Identify security risks
- [ ] Identify integration risks
- [ ] Identify commercial risks
- [ ] Develop risk mitigation strategies

## Phase 6: Legal Due Diligence

### Corporate Structure
- [ ] Verify corporate entity status
- [ ] Review corporate governance
- [ ] Verify authority to sell
- [ ] Review any existing encumbrances
- [ ] Verify clean title to IP

### Litigation Review
- [ ] Conduct litigation search
- [ ] Review any pending or threatened litigation
- [ ] Assess litigation risk
- [ ] Review insurance coverage
- [ ] Evaluate indemnification needs

### Regulatory Review
- [ ] Assess regulatory requirements for target market
- [ ] Review compliance requirements
- [ ] Assess export control restrictions
- [ ] Review data privacy requirements
- [ ] Evaluate regulatory approval needs

### Employment Review
- [ ] Review key personnel agreements
- [ ] Assess retention requirements
- [ ] Review non-compete agreements
- [ ] Evaluate knowledge transfer needs
- [ ] Assess hiring requirements

## Phase 7: Validation Verification

### Test Suite Verification
- [ ] Run test suite locally: `python -m pytest tests/ -q -rs`
- [ ] Verify 338 passed, 17 skipped, 0 failed
- [ ] Run E2E tests: `python -m pytest tests/e2e/ -v`
- [ ] Verify 22 passed, 0 failed
- [ ] Review test skip justifications

### Code Quality Verification
- [ ] Run black: `black --check src tests`
- [ ] Verify all files compliant
- [ ] Run isort: `isort --check-only src tests`
- [ ] Verify all imports compliant
- [ ] Run mypy: `mypy src`
- [ ] Verify no errors

### Security Scan Verification
- [ ] Run bandit: `bandit -r src/`
- [ ] Verify no issues identified
- [ ] Run pip-audit in fresh venv with upgraded pip
- [ ] Verify no known vulnerabilities
- [ ] Run gitleaks: `gitleaks detect --no-git --redact`
- [ ] Verify no secrets in working tree

### Clean Install Verification
- [ ] Create fresh virtual environment
- [ ] Upgrade pip to 26.1.2
- [ ] Install exoarmur-core
- [ ] Run pip-audit
- [ ] Verify zero known vulnerabilities
- [ ] Run exoarmur --help
- [ ] Verify CLI works

## Phase 8: Demo and Pilot

### Demo Execution
- [ ] Run demo script (DEMO_SCRIPT.md)
- [ ] Verify health check: `exoarmur health`
- [ ] Run demo scenarios: `exoarmur demo`
- [ ] Generate demo artifacts
- [ ] Verify artifact structure

### Pilot Planning
- [ ] Define pilot objectives
- [ ] Identify pilot use case
- [ ] Define pilot success criteria
- [ ] Estimate pilot timeline
- [ ] Assess pilot resource requirements

### Pilot Execution
- [ ] Execute pilot integration
- [ ] Monitor pilot performance
- [ ] Collect pilot feedback
- [ ] Assess pilot results
- [ ] Evaluate production readiness

## Phase 9: Post-Acquisition Planning

### Integration Planning
- [ ] Develop integration roadmap
- [ ] Define integration milestones
- [ ] Assign integration resources
- [ ] Establish integration timeline
- [ ] Define integration success criteria

### Team Planning
- [ ] Identify key personnel to retain
- [ ] Develop retention strategy
- [ ] Plan knowledge transfer
- [ ] Assess training needs
- [ ] Define onboarding process

### Technology Planning
- [ ] Plan TrustEvaluator implementation
- [ ] Plan platform executor implementations
- [ ] Plan monitoring infrastructure
- [ ] Plan audit storage integration
- [ ] Plan authentication/authorization integration

### Support Planning
- [ ] Define support model
- [ ] Establish support SLAs
- [ ] Plan support team staffing
- [ ] Define escalation procedures
- [ ] Plan ongoing maintenance

## Phase 10: Decision Making

### Go/No-Go Criteria
- [ ] Define go/no-go criteria
- [ ] Evaluate against criteria
- [ ] Document decision rationale
- [ ] Obtain stakeholder approval
- [ ] Document decision

### Negotiation Planning
- [ ] Define negotiation strategy
- [ ] Identify negotiation points
- [ ] Establish negotiation team
- [ ] Define walk-away position
- [ ] Plan negotiation timeline

### Closing Planning
- [ ] Develop closing checklist
- [ ] Define closing timeline
- [ ] Assign closing responsibilities
- [ ] Plan post-closing integration
- [ ] Define success metrics

## Documentation References

Key documents for due diligence:
- `docs/VALIDATION_MATRIX.md` - Complete validation status
- `docs/KNOWN_LIMITATIONS.md` - Known limitations disclosure
- `docs/acquisition/BUYER_MEMO.md` - Executive summary
- `docs/acquisition/TECHNICAL_DILIGENCE.md` - Technical deep-dive
- `docs/acquisition/IP_ASSET_INVENTORY.md` - IP asset catalog
- `docs/acquisition/BUY_VS_BUILD.md` - Build vs buy analysis
- `docs/acquisition/BUYER_FAQ.md` - Frequently asked questions
- `docs/acquisition/DEMO_SCRIPT.md` - Demonstration script
- `docs/DEPENDENCY_REVIEW.md` - Dependency analysis
- `docs/security/SECURITY_AUDIT_RECEIPT.md` - Security audit status
- `THIRD_PARTY_NOTICES.md` - Third-party license attributions

## Timeline Estimate

- **Phase 1-2 (Screening & Technical):** 2-4 weeks
- **Phase 3-4 (IP & Operational):** 3-5 weeks
- **Phase 5-6 (Commercial & Legal):** 4-6 weeks
- **Phase 7-8 (Validation & Demo):** 2-4 weeks
- **Phase 9-10 (Planning & Decision):** 2-4 weeks

**Total Due Diligence Timeline:** 13-23 weeks (3-6 months)

## Conclusion

This checklist provides a comprehensive framework for evaluating ExoArmur-Core for acquisition. Adjust the scope and depth based on your specific requirements and risk tolerance.

For questions or clarifications, contact the repository owner via GitHub.
