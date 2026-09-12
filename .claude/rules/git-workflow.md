# Git workflow

- Never push directly to `main` — a GitHub ruleset requires CodeQL scanning
  to complete, which only evaluates PRs, not direct pushes.
- Standard flow: `git checkout -b <branch>` → `git push origin <branch>` →
  open a PR on GitHub → wait for the CodeQL check to go green → merge via
  the GitHub UI → `git checkout main && git pull` → delete the branch
  locally and on origin.
- Commit subjects must match Conventional Commits and be ≤72 characters
  (enforced by `.githooks/commit-msg`). Put extra detail in the commit body
  with a second `-m` flag, not a longer subject line.
