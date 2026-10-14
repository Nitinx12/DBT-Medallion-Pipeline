---
name: report-verify
description: Verify the LaTeX technical report build and QA checklist. Use after any reports/ edit, before declaring done.
---

# Report verify

Scope: `reports/` and `reports/scripts/`. Rebuild with
`make report` (writes buildmeta, regenerates CSVs, runs latexmk).

## Log gate (all must hold in `reports/build/main.log`)

- Zero `LaTeX Error`, zero undefined control sequences.
- Zero `Reference ... undefined` / `Citation ... undefined`.
- Zero `Overfull \hbox` over 1pt; underfulls under 5 per chapter.
- Zero `fontspec` missing-font warnings; zero `Missing character`.

## Content gate

- Every number traces to the repo or `reports/data/*.csv` (regenerate
  with `make report-data` after model, test, or page changes).
- Stage list is exactly 0-7 in `pipeline/run_pipeline.ps1` order;
  model counts 9 silver / 8 gold; contracts 8/9/8; GX 6/9/8;
  SQL tests 3/9/7. Trust a recount over memory.
- Every figure and table has a `\cref` reference and a caption with a
  takeaway plus its source.
- `make report-lint` (chktex) is green.
- No secrets, real hosts, or credentials anywhere in sources.
- No `\todo`, lorem, TBD, or XXX markers (the `+1-XXX-XXXX` phone
  pattern in chapter 4 is content, not a marker).

## Fonts gate

All listed fonts embedded subset (parse the PDF; `pdffonts` if
available). Bundled `reports/fonts/` files must never be edited.
