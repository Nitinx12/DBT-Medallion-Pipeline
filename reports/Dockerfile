# Standalone builder for the LaTeX technical report (XeLaTeX).
# Reproducible alternative to a local TeX Live install: TinyTeX plus only
# the packages reports/ needs, with project fonts already bundled.
#
# Build:  docker build -f reports/Dockerfile -t walmart-report .
# Run:    docker run --rm -v "%CD%/reports:/app/reports" walmart-report
#         (mount keeps build/main.pdf and data/*.csv on the host)
#
# Notes:
# - The metrics collector needs only stdlib + PyYAML, so plain pip (not a
#   full `uv sync`) is intentional here to keep the image lean.
# - logs/ is dockerignored, so stage durations render blank unless logs
#   are mounted in; the collector leaves unknown cells empty by design.
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget perl make git fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pyyaml

# TinyTeX (user install, ships XeLaTeX already) + link its binaries onto PATH.
RUN wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh \
    && for dir in /root/.TinyTeX/bin/*; do ln -s "$dir"/* /usr/local/bin/; done \
    && tlmgr install latexmk koma-script pgfplots tcolorbox fontawesome5 \
      siunitx microtype cleveref caption csquotes babel-english setspace \
      chktex makeindex pdfcol environ tools l3packages psnfss pgf lm

WORKDIR /app
COPY . .

# PYTHON=python3 overrides the Makefile's `uv run python`: this image has no
# uv by design (the collector needs only stdlib + PyYAML). latexmk runs as-is.
CMD ["make", "report", "PYTHON=python3"]
