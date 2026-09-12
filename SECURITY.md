# Security Policy

## Reporting a vulnerability
Do **not** open a public issue. Use **Security → Report a vulnerability** or email the maintainer listed in `CODEOWNERS`. Include repro without real credentials.

## What we do
- `.env` / `.env.docker` are git-ignored and never committed (`.gitignore:28`, `.githooks/pre-commit` blocks them, `codeql.yml` scans on push/PR)
- `.env.example` is the only committed env template — rotate any token that was ever committed (`git log -p --all -S "dapi"` or `gitleaks`)
- Dependencies are updated via Dependabot (`.github/dependabot.yml` — weekly pip/docker/actions). Review and merge weekly.

## Supported versions
Only `main` (and the latest `vX.Y.Z` tag) receive fixes. Older tags are not patched — cut a new tag.

## Hardening checklist before production
- [ ] Enable branch protection on `main`/`develop` (see `docs/GIT_WORKFLOW.md`)
- [ ] Require signed commits if org policy demands it
- [ ] Enable secret scanning / push protection in GitHub settings
- [ ] Rotate `DATABRICKS_TOKEN` if it was ever in `.env` history
