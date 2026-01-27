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
| v1.0.0-beta    | Security fixes only |

## Reporting a Vulnerability

If you believe you have found a security vulnerability in ExoArmur Core,
please open a private GitHub Security Advisory or contact the repository
maintainer via GitHub.

Do not open public issues for suspected security vulnerabilities.