# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SELMA is a Python-based lottery (German "Lotto 6 aus 49") prediction and analysis tool. It processes ~70 years of historical lottery draw data (1955–present) and applies structural pattern analysis to score combinations.

## Commands

```bash
python -m selma collect [FROM TO]       # compute stats → collect/
python -m selma optimize [FROM]          # find optimal weights → results/weights.tsv
python -m selma backtest [FROM]          # score actual draws → results/backtest.tsv
python -m selma predict                  # score all combinations → results/predictions_sorted.tsv
python -m selma visualize               # generate HTML dashboard → visualize.html
```

Dependencies: Python 3, NumPy, Matplotlib (`pip install -r requirements.txt`).

## Data Format

Historical draws in `numbers/YYYY.txt` (tab-separated): `Date 1 2 3 4 5 6 SZ`. Numbers 1-49, SZ 0-9 (or -1 for older draws). Dates as YYYY-MM-DD.

## Architecture

The `selma/` package:

- **config.py**: path constants (`BASE_DIR`, `NUMBERS_DIR`, `RESULTS_DIR`, `COLLECT_DIR`)
- **data.py**: `Numbers` — loads all `numbers/*.txt` into a matrix
- **oddeven.py, templates.py, distance.py, sumrange.py, consecutive.py**: structural feature collectors (each has `__init__` for collect, `load()` for predict)
- **hotcold.py**: per-number frequency across time windows (overall, last 20/50/100)
- **profiles.py**: per-number yearly trajectory patterns
- **prediction.py**: orchestration — `collect()`, `predict()`, `backtest()`, `optimize_weights()`
- **visualize.py**: generates self-contained HTML dashboard with Chart.js

## Scoring

Weighted sum of normalized feature probabilities (each divided by its max). Weights stored in `results/weights.tsv`, found via grid search optimization. Features filtered early: combinations with zero probability in any hard feature are skipped.

## Output

- `collect/` — per-feature TSV files (occurrence + frequency), committable
- `results/` — weights, backtest scores, predictions
- `visualize.html` — interactive dashboard
