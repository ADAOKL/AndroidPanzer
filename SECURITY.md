# Security Policy

## Supported Versions

| Version | Supported          |
|---------|-------------------|
| 1.1.x   | ✅ Current        |
| < 1.1   | ❌ Not supported  |

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, report security issues to the maintainers privately using GitHub's [Security Advisory](https://github.com/ADAOKL/android-panzer/security/advisories/new) feature.

### Security Report Details

When reporting, please include:
- **Type**: Command injection, data exposure, privilege escalation, etc.
- **Severity**: Critical, High, Medium, Low
- **Description**: Clear explanation of the vulnerability
- **Reproduction**: Steps to trigger the issue
- **Impact**: What could an attacker do?
- **Suggested Fix** (if any)

We will respond within **48 hours** and work toward a fix.

## Security Features

### Command Injection Prevention
All shell invocations use Python's `shlex.quote()` via the `shq()` utility function (see `apz/util.py`). Untrusted input (package names, file paths, user commands) is always quoted before embedding in shell commands.

### Data Honesty
- Functions are labeled with capability badges: `[ADB]`, `[ROOT]`, `[SDR/HW]`, `[INFO]`, `[GEFAHR]`
- No data fabrication — if a capability requires hardware or lab equipment, it's documented rather than faked
- All limitations are transparent to the user

### Testing
- 137 unit tests covering parsers, security quoting, and forensic workflows
- Mock ADB prevents accidental device interaction during tests
- Automated linting and code style checks via GitHub Actions

## Responsible Disclosure Timeline

1. **Report received**: Acknowledged within 48 hours
2. **Investigation**: We'll work to understand and verify the issue
3. **Fix preparation**: A patch will be developed and tested
4. **Coordinated release**: We'll release a patched version, usually within **14 days**
5. **Public disclosure**: Once the patch is released, the issue becomes public

## Out of Scope

The following are **not** considered security vulnerabilities and should be reported as bugs or feature requests:

- Recommendations to add new features or dependencies
- Issues requiring custom hardware or lab equipment setup
- Social engineering attacks
- Denial of service attacks on the tool itself
- Issues in external dependencies (report to the upstream project)

## License & Compliance

This tool is designed for **authorized forensic analysis and security testing only**. Users are responsible for ensuring they have proper authorization before analyzing any device. Unauthorized access is illegal in most jurisdictions.

---

**Thank you for helping keep Android Panzer secure!**
