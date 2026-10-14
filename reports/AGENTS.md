# AGENTS.md

Instructions for AI coding agents working on the LaTeX technical report.
Scope: `reports/` (document, figures, data) and `reports/scripts/`
(collectors). The dbt and Airflow pipeline is out of scope unless the
task says otherwise.

Read this file fully before touching anything under `reports/`. Then
check `.claude/skills/` for a skill that matches the task (`report-verify`,
`report-extend`) and follow it.

## 1. What this project is

A XeLaTeX (`scrreprt`, DIV=12) technical report for the Walmart medallion
pipeline: 13 chapters plus 7 appendices, 14 TikZ diagrams, 8 pgfplots
charts generated from `reports/data/*.csv`. Output is `build/main.pdf`
(released copy: `report.pdf`). Previous edition preserved at
`legacy/report_v1.tex`. Entry point is `reports/main.tex`, which only
inputs style files and chapters.

## 2. Repo map

```
reports/main.tex                  inputs styles + chapters only
reports/latex/                    design system (never hard-code in chapters)
reports/chapters/                 00_ front matter, 01-13 content, appendix_*
reports/figures/tikz/             one vector diagram per file
reports/scripts/                  collect_metrics.py, write_buildmeta.py
reports/data/                     generated CSVs (committed, small)
reports/fonts/                    bundled OFL fonts (never edit)
reports/Dockerfile                clean-room builder (build deferred)
```

## 3. Commands

Always use `uv`. Never `pip install` and never bare `python`.

```
make report-data   # scan repo into data/*.csv (never invents numbers)
make report        # write buildmeta + compile with latexmk (XeLaTeX)
make report-lint   # chktex style checks
uv run pytest tests/unit/test_collect_metrics.py
```

## 4. Content rules (non negotiable)

1. **Truth over decoration.** Every number traces to the repo or
   `data/*.csv`. Unverifiable values are omitted; illustrative data is
   labelled *illustrative* in its caption.
2. **Design tokens only.** Colors, fonts, spacing and box styles live in
   `latex/` and are referenced by name. No hex, no font switches, no
   manual spacing in chapters or figures.
3. **Every figure and table** gets a `\cref` reference and a caption with
   a one-sentence takeaway plus its source.
4. **Listings are excerpts** (25 lines max) that exist verbatim in the
   repo, with a file-path title bar.
5. **No secrets.** Env var names only, never values, hosts, or tokens.

## 5. LaTeX rules that bite (learned the hard way)

- Text block is 157mm (DIV=12). Size every diagram and table to fit;
  never `resizebox` text under 7.5pt.
- pgfplots tables need `col sep=comma`; symbolic coords cannot hold
  underscores (use numeric x plus explicit tick labels).
- `\file{}` / `\cmd{}` take plain text (`_` not `\_`, no macros or
  braces inside) so paths stay breakable.
- Table columns holding paths or commands must be `p{}` widths;
  `l` columns never wrap.
- `make report-lint` must stay green; its `-n` flags document
  chktex's blind spots (code listings, `\file{}` contents).

## 6. Code style

Python collectors follow repo style: type hints, docstrings, `uv run`
ruff check/format clean, fixture-tree unit tests for new logic.

## 7. Git hygiene

- Work on a branch named `fix/<short topic>` or `feat/<short topic>`.
- One logical change per commit. Commit message format:
  `type(scope): short summary` (`docs(report): ...` for prose).
- Stage files by name. Never commit `build/`, caches, or `buildmeta.tex`
  (generated, gitignored).
- Never rewrite shared history. No force push.

## 8. Definition of done

A task is done only when all of these hold:

1. `make report` builds with zero LaTeX errors, zero undefined refs,
   zero overfull boxes over 1pt.
2. `make report-data` output is committed alongside source changes.
3. `make report-lint` is green.
4. All fonts embedded; every number re-verified against the repo.
5. No secret, stray `\todo`, or debugging output was introduced.
6. The final message lists: files changed, what and why, how it was
   verified, and anything left open.

## 9. When to stop and ask

Stop and ask the owner before:
* Changing gold table columns, dbt models, the schema or any Airflow DAG.
* Pulling metrics from the live Neon database.
* Enabling `-shell-escape` (minted) or adding a paid service.
* Bundling a font whose licence is not SIL OFL or equivalent.

## 10. Skills available

* `report-verify`: rebuild plus log, content, and fonts gates.
* `report-extend`: add chapters, charts, and diagrams the right way.
