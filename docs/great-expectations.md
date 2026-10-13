# Great Expectations

Final gate after Gold SQL tests. All GX code lives in `gx/`: suites in `gx/suites/` (bronze/silver/gold), context in `gx/context.py`, runner in `gx/run.py`.

```bash
uv run python -m gx.run --layer all
uv run python -m gx.run --layer bronze
```

- Suites generated via `great_expectations` API, stored in `gx/expectations/` (git-ignored, generated).
- Validations run as GX checkpoint per layer; failures block pipeline (same exit-code gate).
- Artifacts in `gx/uncommitted/` (ignored).

See `tests.md`, `pipeline.md` Stage 7.
