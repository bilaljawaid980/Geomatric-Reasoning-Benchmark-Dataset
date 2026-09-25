# Security Policy

## Reporting a vulnerability

Please do not disclose security vulnerabilities in a public issue.

Use GitHub's private vulnerability reporting for this repository:

1. Open the repository's **Security** tab.
2. Select **Advisories**.
3. Select **Report a vulnerability**.

Include the affected file or component, reproduction steps, potential impact, and any suggested mitigation. You should receive an acknowledgement within seven days.

## Credentials and research data

- Store API credentials only in environment variables or an untracked `.env` file.
- Treat model-provider logs and raw responses as potentially sensitive until reviewed.
- Revoke and rotate any credential that is accidentally committed, even if the commit is later removed.
- Do not include private, proprietary, or personally identifying data in benchmark contributions.

Only the latest revision on `main` is supported with security fixes.
