# Contributing to GRIP

Thank you for helping improve GRIP.

## Before opening a change

1. Open an issue for substantial dataset, schema, scoring, or protocol changes.
2. Create a focused branch from `main`.
3. Keep generated scenes deterministic: record seeds and preserve the latent state used to compute ground truth.
4. Never commit credentials, `.env` files, private model data, or local machine paths.
5. Do not commit generated files that exceed GitHub's 100 MB per-file limit.

## Development setup

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

API-backed evaluations require environment variables documented in `.env.example`. Offline generation, validation, scoring, and reporting should remain usable without API credentials wherever possible.

## Pull requests

- Explain the motivation and scope.
- List commands used to validate the change.
- Report any changes to dataset counts, answer keys, schemas, or published metrics.
- Avoid unrelated formatting or generated-output churn.
- Confirm that `gitleaks git . --redact` reports no secrets.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
