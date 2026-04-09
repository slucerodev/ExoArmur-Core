# Security Policy

## Security Scanning

ExoArmur uses automated security scanning on all changes:

- **Dependency scan**: `pip-audit` — checks for known vulnerabilities in dependencies
- **SAST**: `bandit -r src` — static analysis for security issues in Python code
- **Secret scan**: `gitleaks detect --no-git --redact --config .gitleaks.toml` — ensures no secrets exist in the current working tree

Full-history scanning may flag legacy false positives in historical commits;
the release security gate verifies current working tree cleanliness.

## Supported Versions

| Version        | Supported |
| -------------- | --------- |
| Architecture / Contract: v1.0.0 | Security fixes and backported criticals |
| Package (pip): 2.0.0 | Security fixes and backported criticals |

## Reporting a Vulnerability

If you believe you have found a security vulnerability in ExoArmur Core,
please open a private GitHub Security Advisory or contact the repository
maintainer via GitHub.

Do not open public issues for suspected security vulnerabilities.

## What to Include in a Report

When reporting a security vulnerability, please include:

- **Description**: Clear description of the vulnerability
- **Impact**: Assessment of potential impact
- **Reproduction steps**: Detailed steps to reproduce the issue
- **Environment**: Version information and environment details
- **Proof of concept**: Code or configuration demonstrating the vulnerability (if applicable)

## Response Timeline

- **Acknowledgement**: 48-72 hours - Initial response confirming receipt
- **Triage**: 3-5 business days - Investigation and severity assessment
- **Resolution**: Timeline depends on severity and complexity
- **Disclosure**: Coordinated disclosure with affected parties

## Disclosure Process

### Private Disclosure
- All security reports are handled privately
- GitHub Security Advisories are preferred for coordinated disclosure
- Direct contact via GitHub is available for sensitive issues

### Public Disclosure
- Public disclosure occurs after fixes are available
- Security advisories will be published with appropriate credit
- Disclosure timeline coordinated with reporter preferences

### Credit and Recognition
- Security researchers will be acknowledged in security advisories
- Credit preferences (name/anonymous) respected
- Coordinated disclosure timeline honored

## Security Scope

This security policy applies to:

- **ExoArmur Core source code** in the main repository
- **Official documentation** and configuration files
- **Build and deployment scripts** in the repository
- **Dependencies** explicitly declared in the project

### Out of Scope

The following are generally out of scope for security reports:

- **Third-party dependencies** (report directly to vendors)
- **Documentation typos** (use regular issues)
- **Performance issues** without security impact
- **Vulnerabilities in user deployments** not present in source code
- **Theoretical vulnerabilities** without practical exploit

## Threat Model Summary

ExoArmur is designed to reduce the impact of four primary threat classes:

- **Policy evasion**: direct executor invocation, post-evaluation intent mutation, race conditions, and privilege escalation attempts.
- **Audit tampering**: deletion, modification, or injection of audit records, or compromise of the audit storage layer.
- **Safety override**: attempts to bypass safety gate decisions or change safety constraint configurations.
- **Executor compromise**: malicious or sandbox-escaping executor modules.

Primary defenses include the single `ProxyPipeline` execution boundary, read-only `ActionIntent` handling within the governance path, deterministic policy and safety evaluation, the untrusted executor model, and tamper-evident audit records with JetStream-backed persistence when configured.

This summary is intentionally high-level. The full threat and failure model is documented in `docs/EXOARMUR_SYSTEMS_PAPER.md`.

## Executor Runtime Boundary

Executors are treated as untrusted capability modules at runtime.

- Executors receive only the governed action input and return an execution result; they do not participate in policy, safety, or approval decisions.
- Executors cannot bypass the `ProxyPipeline` boundary, mutate audit records, or access governance internals directly.
- Policy and safety checks run before dispatch, and approval is required when the governing policy demands it.
- If an executor is compromised, the expected blast radius is limited to that capability module; governance state remains isolated.

## Security Best Practices

### For Users
- Keep dependencies updated through regular package updates
- Review security advisories for your deployed versions
- Follow principle of least privilege in deployments
- Monitor audit logs for unusual activity

### For Developers
- Follow secure coding practices outlined in CONTRIBUTING.md
- Use provided security scanning tools in development
- Report security concerns through proper channels
- Maintain separation of concerns between governance and execution

## Security Architecture

ExoArmur's security model is based on:

- **ProxyPipeline execution boundary** - All actions pass through governance controls
- **Locked contracts** - V1 contracts are protected by repository policy and cannot be modified to bypass security
- **Deterministic audit trails** - All actions are logged and replayable
- **Feature flag isolation** - New capabilities are gated behind explicit controls

## Contact Information

For security-related inquiries:

- **GitHub Security Advisory**: Preferred method for vulnerability reports
- **Repository Maintainer**: Available via GitHub direct messaging
- **Emergency Contact**: Use GitHub Security Advisory for urgent issues

Thank you for helping keep ExoArmur Core secure.