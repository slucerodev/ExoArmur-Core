# Security Policy

## Security Scanning

ExoArmur uses automated security scanning on all changes:

- **Dependency scan**: `pip-audit` - Checks for known vulnerabilities in dependencies
- **SAST**: `bandit -r src` - Static analysis for security issues in Python code
- **Secret scan**: `gitleaks detect --no-git --redact --config .gitleaks.toml` - Ensures no secrets in current working tree

History scanning may flag legacy false positives; the release gate verifies current working tree cleanliness.

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc.
