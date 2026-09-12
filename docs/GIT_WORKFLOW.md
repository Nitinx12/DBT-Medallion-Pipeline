# Git Workflow — Production Guide

> One logical pipeline, three runners. One branching model. No direct pushes to `main`.

This document defines the **production git workflow** before the first release. It does not change pipeline logic (`pipeline/run_pipeline.ps1`, Airflow DAG, `scripts/*`, `utils/*`).

---

## 1. Branching model

```
main      ──────●────────●────────●──▶  production, always deployable, protected
                ▲        ▲        ▲
                │        │        │
develop   ──●───●──●─────●──●─────●──▶  integration, next release
             \   \   \     \   \
feature/*    ●    ●   ●     ●   ●    ▶  one feature/fix per branch, short-lived
release/*                 ●────────▶    stabilization, version bump, tag vX.Y.Z
hotfix/*                          ●──▶  urgent prod fix from main
```

| Branch | Purpose | CI | CD | Protected |
|---|---|---|---|---|
| `main` | Production — every commit is a potential release | full 5-job gate | publishes `latest` + SHA to GHCR (via `cd.yml` only after CI passes) | **yes** — no direct push, PR + review + CI required |
| `develop` | Integration — merges all `feature/*` before `main` | same 5-job gate | none | **yes** — PR required |
| `feature/<scope>-<slug>` | Single logical change | lint/unit/dag/docker (+ commitlint on PR) | none | no — push freely, PR to `develop` |
| `release/vX.Y.Z` | Freeze, bump `pyproject.toml` version, fix only | full gate | none until tagged | yes |
| `hotfix/<slug>` | Urgent fix branched from `main` | full gate | via release after merge | no |
| `vX.Y.Z` (tag) | Immutable release | `release.yml` builds & pushes semver images | publishes `vX.Y.Z`, `vX.Y`, `vX` to GHCR + GitHub Release | protected via `release.yml` semver check |

Branch naming enforcement: `feature/*`, `release/*`, `hotfix/*`, `chore/*`, `docs/*`, `ci/*` — anything else should be rejected in review.

---

## 2. Commit message contract

`AGENTS.md` already mandates:

```
Present tense, short summary (<= 50 chars)
prefix by area:  extract:, dbt:, airflow:, docker:, tests:, utils:, docs:
```

Production enforces **Conventional Commits** (checked by `.github/workflows/commitlint.yml` on every PR to `main`/`develop`):

```
<type>(optional scope): <summary>

Types: feat, fix, docs, chore, refactor, test, ci, build, perf, style, revert
```

| Good | Bad |
|---|---|
| `feat(extract): fallback to append-only when no unique index` | `added script for databricks` (no type) |
| `fix(dbt): pin dbt-postgres to 1.11.0` | `gx updated` (vague) |
| `ci: serialize GHCR publishing to avoid race` | `just checking` (noise) |
| `docs(ci_cd): clarify workflow_run gate` | `minor updated in project` (not actionable) |

Why: `release.yml` and `softprops/action-gh-release` auto-generate release notes from these prefixes. Bad messages = useless changelog.

---

## 3. Working locally

```bash
# One-time setup
git config user.name "Your Name"
git config user.email "you@company.com"
git pull --rebase   # AGENTS.md rule — rebase, not merge

# Start a feature (from develop, never from main)
git fetch origin
git checkout develop
git pull --rebase
git checkout -b feature/extract-watermark-fallback

# Work: one file / one logical change per commit
git add scripts/extract.py
git commit -m "feat(extract): fallback to append-only when no unique index"
#   and body line if why is not obvious:
# git commit -m "fix(docker): pin JDK to 17" -m "PySpark 3.5.x mongo connector is untested on JDK 21"

# Keep in sync before pushing (rebase, no merge commits)
git fetch origin
git rebase origin/develop

# Push and open PR to develop
git push -u origin feature/extract-watermark-fallback
# open PR: feature/* -> develop  (template auto-applies)

# After review + CI green, squash or rebase-merge into develop
# Develop -> main via PR only, when ready to release

# Release
git checkout main
git pull --rebase
git checkout -b release/v1.2.0
# bump pyproject.toml version = "1.2.0", update CHANGELOG if any
git commit -m "chore(release): bump to v1.2.0"
git push -u origin release/v1.2.0
# PR: release/v1.2.0 -> main, full CI, review
# After merge to main:
git checkout main
git pull --rebase
git tag -a v1.2.0 -m "release: v1.2.0"
git push origin v1.2.0   # triggers release.yml -> versioned GHCR images + GitHub Release

# Hotfix (from main)
git checkout main
git pull --rebase
git checkout -b hotfix/dbt-silver-null-guard
# fix, test, PR hotfix/* -> main (and cherry-pick or PR to develop)
```

---

## 4. CI / CD — what runs when

| Event | Workflow | Jobs |
|---|---|---|
| PR to `main` or `develop` | `ci.yml` + `commitlint.yml` | lint → unit-tests / dag-integrity / docker-build → integration (full Postgres medallion gate) |
| Push to `main` or `develop` | `ci.yml` | same 5 jobs |
| Push tag `v*.*.*` | `release.yml` | validates semver, builds & pushes `vX.Y.Z` / `vX.Y` / `vX` + SHA, creates GitHub Release |
| `CI` succeeds on `main` | `cd.yml` (workflow_run) | publishes rolling `latest` + SHA images |
| Any push/PR | `codeql.yml` | security scan (actions + python) |

`cd.yml` **only** publishes `latest` — immutable versioned images come only from `release.yml`. Do not push version tags manually without a PR.

---

## 5. Branch protection (GitHub Settings → Branches)

Enable for `main` and `develop`:

- [x] Require a pull request before merging (1 approval, CODEOWNERS required)
- [x] Require status checks to pass: `lint`, `unit-tests`, `dag-integrity`, `docker-build`, `integration`, `commitlint`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings
- [x] Restrict pushes — no direct push to `main`/`develop` (admin included is ideal)
- For `main` only: Require signed commits (if org mandates)

Via API / `gh` (admin-only, run once):

```bash
gh api repos/Nitinx12/Walmart_DBT/branches/main/protection -X PUT -f required_status_checks='{"strict":true,"contexts":["lint","unit-tests","dag-integrity","docker-build","integration"]}' -f enforce_admins=true -f required_pull_request_reviews='{"required_approving_review_count":1,"require_code_owner_reviews":true}' -f restrictions=null
```

Or use the newer Rulesets UI (Settings → Rules → Rulesets) to enforce the same.

---

## 6. What was wrong before (audit 2026-09-12, 158 commits)

All fixes land on branch `chore/git-workflow-production-ready` — **no pipeline logic changed**.

| # | Mistake | Evidence | Fix in this branch |
|---|---|---|---|
| 1 | **No branching — 158 commits straight to `main`** | `git branch -a` shows only `main`; `git log --graph` is linear | This branch is the first feature branch; `GIT_WORKFLOW.md` defines `main`/`develop`/`feature/*`/`release/*` |
| 2 | **No branch protection / empty rulesets** | `gh api .../rulesets` = `[]`, no protection | `CODEOWNERS` + protection checklist in this doc (settings change, not file) |
| 3 | **Inconsistent identity — two emails** | `Nitin <nitin321x@gmail.com>` and `Nitin <Nitin85x@gmail.com>` | Document single `user.email` in §3; run `git config user.email` once |
| 4 | **`pull.rebase` mismatch** | `AGENTS.md` says `git pull --rebase` but `git config pull.rebase` = `false` | Add `git config pull.rebase true` to onboarding (§3); CI unchanged |
| 5 | **~40% commit messages violate AGENTS.md / Conventional Commits** | `gx updated`, `just checking`, `tatus remove junk file`, `minor updated` (64/158 checked) | `commitlint.yml` workflow + `pull_request_template.md` title rule |
| 6 | **Typos and noise commits** | `tatus`, `Great Expection`, `secuirty`, `try to fixed...`, `just checking` | Template + commitlint + squash-merge policy avoids polluting `main` |
| 7 | **Bundled unrelated changes** | `0d6ff05` touches 16 files across dashboard/pipeline/utils/scripts/tatus; `b5a9469` mixes Makefile + 23 GX JSON re-formats | `pull_request_template.md` “One logical change only” + CODEOWNERS |
| 8 | **CI used as debugger (10+ “try to fix” commits)** | `395e08f`, `134ba76`, `ba767de`, `e3b5ddb`, etc. | Feature branches: push to `feature/*`, CI gives feedback before `main` |
| 9 | **Generated artifacts churn in git** | `gx/expectations/*.json` committed then bulk-deleted in `92880d5` (1693 deletions), reformatted monthly, `jars/*.jar` binaries, `reports/charts/*.png` | `.gitignore` already ignores `gx/expectations` + `gx/uncommitted`; this branch fixes malformed line (see #11) and documents “no generated artifacts” in PR template |
| 10 | **No releases / tags / changelog** | `git tag` empty, `pyproject.toml` still `0.1.0`, `cd.yml` only pushes `latest`+SHA | `release.yml` (semver gate + GHCR `vX.Y.Z` + GitHub Release), version bump on `release/*` |
| 11 | **Malformed `.gitignore` line 150** | `__init__.pyreports/asset/pipeline.mp4` (missing newline, concatenates two patterns) | Fixed: split into `__init__.py` and `reports/asset/pipeline.mp4` |
| 12 | **No `.env.example`** | `.env` + `.env.docker` on disk (secrets, Databricks token), no example for onboarding, risk of leaking real values | Added `.env.example` with placeholders |
| 13 | **CI only on `main` push/PR** | `ci.yml: on.pull_request.branches: [main]` + `push.branches: [main]` — feature pushes get no early feedback unless a PR exists | `ci.yml` now: `pull_request: [main, develop]` + `push: [main, develop]` + `tags: v*.*.*` + `workflow_dispatch` |
| 14 | **No `CONTRIBUTING` / PR template / CODEOWNERS** | `.github/` only had workflows + `mocks/.gitkeep` | Added `CODEOWNERS`, `pull_request_template.md`, `dependabot.yml`, this doc |
| 15 | **CD race + “latest moves every commit”** | `cd.yml` concurrency `publish-ghcr` serializes but `latest` still advances on every CI-passed commit, no immutable version | Split: `cd.yml` owns rolling `latest`+SHA, `release.yml` owns immutable semver — manager picks release cadence |
| 16 | **`.gitignore` silently ignores `.env.docker` but `docker/.env` also untracked** | `docker/.env` appears in `git status --ignored` but pattern only covers `.env.*` at root | Already covered (`.env.*` + `docker/.env` via `git status --ignored`), keep as-is; onboarding uses `.env.example` |

---

## 7. Manager checklist before first production release

1. **Create `develop` branch from `main`** (one-time):
   ```bash
   git checkout main && git pull --rebase
   git checkout -b develop && git push -u origin develop
   ```
2. **Enable branch protection** for `main` and `develop` (Settings → Branches → Add rule, or Rulesets).
3. **Require this branch’s workflows to pass**: `lint`, `unit-tests`, `dag-integrity`, `docker-build`, `integration`, `commitlint`.
4. **Set `pull.rebase` default for the team**: `git config --global pull.rebase true` (aligns with `AGENTS.md`).
5. **Rotate any token that was ever committed** (search `git log -p --all -S "dapi"` — `.env` was correctly ignored but verify history).
6. **First release**: merge this workflow branch → `develop` → PR `develop` → `main` → tag `v0.1.0` (or `v1.0.0` if prod-ready) → `release.yml` publishes versioned images.
7. **Turn on Dependabot** (already configured via `.github/dependabot.yml` — approve weekly PRs).

After this branch merges, **no one pushes to `main` directly**. Every change is `feature/*` → PR → `develop` → PR → `main` → tag.
