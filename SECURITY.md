# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in PacketArch, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please use one of the following methods:

1. **GitHub Security Advisories** (preferred): Use the [Security tab](https://github.com/ip-aegis/PacketArch/security/advisories) to create a private advisory
2. **Email**: Contact the maintainers directly via the email listed in the repository

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix timeline**: Depends on severity, typically within 30 days for critical issues

## Scope

The following are in scope for security reports:
- Authentication and authorization bypasses
- SQL injection, XSS, CSRF
- Credential exposure
- Remote code execution
- Privilege escalation
- Insecure default configurations

The following are out of scope:
- Self-signed certificate warnings (expected behavior)
- Denial of service on development endpoints
- Issues requiring physical access to the server

## Supported Versions

Security updates are applied to the latest version on the `master` branch.
