# Great Expectations

Final gate after Gold SQL tests. Suites in `pipeline/data_quality/suites/` (bronze/silver/gold), run via `pipeline/data_quality/run.py`.

```bash
uv run python -m pipeline.data_quality.run --layer all
uv run python -m pipeline.data_quality.run --layer bronze
```

- Suites generated via `great_expectations` API, stored in `gx/expectations/` (git-ignored, generated).
- Validations run as GX checkpoint per layer; failures block pipeline (same exit-code gate).
- Artifacts in `gx/uncommitted/` (ignored).

See `tests.md`, `pipeline.md` Stage 7.
