# Technical Report

Full technical report for the Walmart medallion pipeline: architecture,
extraction, silver and gold models, orchestration, quality gates, data
contracts, dashboard, CI/CD, operations, and measured results.
13 chapters plus 7 appendices, 14 TikZ diagrams, 8 data-driven charts.
Engine is XeLaTeX (`scrreprt`); output is `build/main.pdf`, with the
released copy at `report.pdf`.

## Build

```bash
make report-data   # scan the repo into data/*.csv
make report        # write buildmeta + compile to build/main.pdf
make report-lint   # chktex style checks
```

Needs TeX Live with XeLaTeX (`latexmk`). Fonts (Inter, JetBrains Mono,
both OFL) are bundled in `fonts/`, so the build never depends on machine
fonts. Prefer the Docker route (`reports/Dockerfile`) for a clean room.

## Layout

- `main.tex` — inputs style files and chapters, nothing else.
- `latex/` — the whole design system: colors, fonts, layout,
  callout boxes, code listings, TikZ and pgfplots styles, macros.
  Chapters use these names, never raw values.
- `chapters/` — `00_` front matter, `01`–`13` content (executive
  summary written last), `appendix_a`–`g` (inventory, commands,
  env vars, glossary, ERD, contract sample, changelog).
- `figures/tikz/` — 14 vector diagrams, one file each.
- `scripts/` — `collect_metrics.py` builds `data/*.csv` from the repo
  (file counts, contract fields, log timestamps); unknown cells stay
  empty and missing inputs fail instead of fabricating.
  `write_buildmeta.py` injects version, commit SHA and date.
- `data/` — generated CSVs, committed; regenerate after model, test,
  or page changes before rebuilding.
- `legacy/report_v1.tex` — the previous `article`-class report, kept.
