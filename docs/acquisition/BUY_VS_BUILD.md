# Buy vs Build Analysis

*Prepared for: Prospective Acquirers and Strategic Buyers*
*Date: June 1, 2026*
*Version: 2.1.0*

## Executive Summary

This analysis compares the cost and timeline of acquiring ExoArmur-Core versus building an equivalent deterministic governance kernel from scratch.

## Build-From-Scratch Analysis

### Core Components Required

To build an equivalent system from scratch, the following components would need to be implemented:

| Component | Complexity | Est. Effort | Risk |
|-----------|------------|-------------|------|
| Deterministic clock abstraction | Low | 2-3 weeks | Low |
| Canonical JSON encoding | Low | 1-2 weeks | Low |
| Deterministic ID generation (ULID) | Low | 1-2 weeks | Low |
| ProxyPipeline execution boundary | High | 8-12 weeks | High |
| Policy evaluation engine | High | 6-10 weeks | High |
| Safety evaluation engine | High | 6-10 weeks | High |
| Replay verification engine | High | 8-12 weeks | High |
| Cryptographic audit trails | High | 6-10 weeks | High |
| Plugin architecture | Medium | 4-6 weeks | Medium |
| FileSystemExecutor | Medium | 4-6 weeks | Medium |
| DatabaseExecutor | Medium | 4-6 weeks | Medium |
| Test suite (338 tests) | High | 12-16 weeks | High |
| Documentation | Medium | 6-8 weeks | Medium |
| CI/CD infrastructure | Medium | 4-6 weeks | Medium |

### Total Build Effort

**Timeline:** 12-18 months (optimistic) to 24-36 months (realistic)

**Resource Requirements:**
- 2-3 senior engineers (security, distributed systems, cryptography)
- 1-2 QA engineers (test automation, security testing)
- 1 technical writer (documentation)
- 1 DevOps engineer (CI/CD, infrastructure)

**Total Cost Estimate:**
- Engineering: $1.2M - $2.4M (12-24 months at $100k-150k/month)
- QA: $300k - $600k
- Documentation: $150k - $300k
- DevOps: $150k - $300k
- **Total: $1.8M - $3.6M**

### Build Risks

**Technical Risks:**
- Determinism bugs are difficult to detect and debug
- Cryptographic implementation errors can have severe security consequences
- Replay verification requires deep understanding of distributed systems
- Test suite for determinism requires specialized expertise

**Timeline Risks:**
- Underestimation of complexity (common in governance systems)
- Integration challenges between components
- Security audit delays
- Regulatory compliance requirements

**Opportunity Cost:**
- Delay to market (12-36 months)
- Team distraction from core business
- Opportunity cost of not having governance during development

## Acquisition Analysis

### Acquisition Benefits

**Immediate Availability:**
- Internally validated code available immediately
- Comprehensive test suite (338 tests)
- Complete documentation
- CI/CD infrastructure in place

**Technical Excellence:**
- High code quality (black/isort/mypy clean)
- Clean security scan results (bandit/pip-audit clean)
- Well-architected system with clear separation of concerns
- Minimal codebase for maintainability (~5,453 lines)

**Reduced Risk:**
- No technical implementation risk
- No security implementation risk
- No timeline uncertainty
- Proven determinism via comprehensive testing

**Cost Savings:**
- Avoid $1.8M - $3.6M build cost
- Avoid 12-36 month delay to market
- Avoid ongoing maintenance burden for custom implementation

### Acquisition Costs

**Acquisition Price:** TBD (negotiable)

**Integration Costs:**
- TrustEvaluator implementation: $100k - $200k
- Platform executor implementations: $200k - $400k
- Production monitoring infrastructure: $100k - $200k
- Legal review of license: $50k - $100k
- **Total Integration: $450k - $900k**

**Ongoing Costs:**
- Maintenance: $100k - $200k/year
- Security updates: $50k - $100k/year
- **Total Ongoing: $150k - $300k/year**

### Acquisition Risks

**Technical Risks:**
- Integration with existing systems may require adaptation
- TrustEvaluator and platform executors require implementation
- No third-party security audit (self-validated only)

**Timeline Risks:**
- Due diligence process (4-8 weeks)
- Integration work (8-16 weeks)
- **Total: 12-24 weeks to production**

**Commercial Risks:**
- License terms may require negotiation
- Support and maintenance terms need definition
- IP transfer and assignment require legal review

## Comparative Analysis

### Timeline Comparison

| Approach | Time to Production | Risk Level |
|----------|-------------------|------------|
| Build from scratch | 12-36 months | High |
| Acquire ExoArmur | 3-6 months | Low |

### Cost Comparison

| Approach | Upfront Cost | First Year Total | 3-Year Total |
|----------|--------------|------------------|--------------|
| Build from scratch | $1.8M - $3.6M | $2.0M - $4.0M | $2.5M - $5.0M |
| Acquire ExoArmur | Acquisition + $450k - $900k | Acquisition + $600k - $1.2M | Acquisition + $900k - $1.8M |

**Break-even Analysis:**
- If acquisition price ≤ $1.4M, acquisition is cheaper in year 1
- If acquisition price ≤ $2.7M, acquisition is cheaper over 3 years

### Risk Comparison

| Risk Category | Build Risk | Acquisition Risk |
|---------------|------------|-----------------|
| Technical implementation | High | Low |
| Security implementation | High | Low |
| Timeline certainty | Low | High |
| Integration complexity | N/A | Medium |
| Third-party audit | Required | Required (both) |
| Regulatory compliance | Required | Required (both) |

## Strategic Considerations

### When to Build

Building from scratch may be preferable if:
- Governance requirements are highly specialized and don't match ExoArmur's design
- Existing technology stack is incompatible with Python
- Regulatory requirements demand complete control over all components
- Organization has excess engineering capacity and wants to build internal expertise
- Long-term strategic differentiation requires custom implementation

### When to Buy

Acquiring ExoArmur is preferable if:
- Time to market is critical
- Governance requirements align with ExoArmur's design
- Organization wants to focus on core business, not infrastructure
- Budget is constrained compared to build cost
- Risk tolerance is low for security-critical systems
- Organization wants to leverage existing expertise and best practices

## Recommendation

**Primary Recommendation: Acquire ExoArmur-Core**

**Rationale:**
1. **Significant cost savings** - Acquisition is $1M+ cheaper than building
2. **Faster time to market** - 3-6 months vs 12-36 months
3. **Lower risk** - Proven implementation vs unproven build
4. **High quality** - Clean code, comprehensive tests, security scans clean
5. **Extensible** - Plugin architecture allows customization

**Conditions for Acquisition:**
1. Acquisition price ≤ $2.7M (3-year break-even)
2. Governance requirements align with ExoArmur's design
3. Organization can allocate $450k - $900k for integration
4. Organization accepts self-validated security (no third-party audit)
5. Legal review of license terms is acceptable

**Post-Acquisition Priorities:**
1. Implement TrustEvaluator for production trust scoring
2. Implement platform executors for required vendor integrations
3. Add production monitoring and observability
4. Conduct third-party security audit
5. Obtain formal verification for DACT Level 6

## Conclusion

Acquiring ExoArmur-Core offers significant advantages over building from scratch in terms of cost, timeline, and risk. The system is ready for private NDA evaluation and IP-only sale diligence with comprehensive internal validation, with clear path to production deployment through targeted integration work. Note: This is a reference implementation with no third-party security audit, not production-certified.

The primary decision factor is acquisition price. At or below $2.7M, acquisition is economically superior over a 3-year horizon. Above this threshold, build-from-scratch becomes economically competitive but carries significantly higher technical and timeline risk.
