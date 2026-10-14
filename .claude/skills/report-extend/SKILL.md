---
name: report-extend
description: Add report chapters, charts, or diagrams the right way. Use for any technical-report enhancement.
---

# Report extend

Scope: `reports/` and `reports/scripts/`. Read `reports/README.md`
and `reports/AGENTS.md` first.

## Data first

- New chart? Extend `reports/scripts/collect_metrics.py` first
  (plus its fixture-tree unit test), regenerate with
  `make report-data`, then plot from `data/*.csv` with the shared
  `wm` pgfplots styles. Never hand-plot invented numbers; unknown
  cells stay empty.
- New chapter? Open with a `\chapterlead`, add an `glance` box, close
  with a `keybox`, and reference every figure/table with `\cref`.
- New diagram? One file in `figures/tikz/` using `latex/tikz-styles.tex`
  only, sized to the 157mm text block (DIV=12). No `resizebox` shrinking
  text under 7.5pt.

## Rules that bite

- Style tokens live in `latex/` (colors, fonts, boxes, listings).
  Never hard-code hex, fonts, or spacing in chapters.
- Paths and commands go through `\file{}` / `\cmd{}` with plain-text
  arguments (`_` not `\_`, no macros or braces inside).
- Table columns that hold paths or commands must be `p{}` widths;
  `l` columns never wrap.
- pgfplots tables need `col sep=comma`; symbolic coords cannot contain
  underscores (use numeric x plus explicit tick labels).
- Excerpts stay under 25 lines and must exist verbatim in the repo.
- Finish with `report-verify` (full rebuild plus log gates).
