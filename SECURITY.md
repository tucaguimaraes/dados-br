# Security Policy

## Supported Versions

Only the latest released version of `dados-br` receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, **please do not open a public GitHub issue**.

Instead, report it privately by emailing:

**arturguimaraes@gmail.com**

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- The version of `dados-br` affected
- Any suggested fix (optional but appreciated)

We will acknowledge your report within **72 hours** and aim to release a fix within **14 days** for confirmed critical issues.

## Scope

Security issues relevant to this project include:

- Malicious YAML catalog entries that could lead to arbitrary code execution or path traversal
- SSL/TLS certificate verification bypass vulnerabilities
- Download redirect attacks (SSRF-like behavior)
- Dependency vulnerabilities with a known CVE

Out of scope (but still appreciated):

- Vulnerabilities in public datasets themselves (report to the source agency)
- Issues requiring physical access to the machine
- Social engineering

## Responsible Disclosure

We follow responsible disclosure principles. Reporters who act in good faith will be credited in the release notes (unless they prefer anonymity).
