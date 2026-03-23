# SELMA

Statistical analysis and prediction tool for the German lottery "Lotto 6 aus 49". Processes ~70 years of historical draw data (1955–present) and applies structural pattern analysis to score combinations.

**Dashboard**: [riasc.github.io/SELMA](https://riasc.github.io/SELMA/)

## Setup

```bash
conda create -n selma python=3
conda activate selma
pip install -r requirements.txt
```

## Usage

### 1. Collect statistics

Compute occurrences and frequencies from historical data:

```bash
python -m selma collect                          # all data, frequencies from 2000-01-01
python -m selma collect 2000-01-01 2025-12-31    # exclude 2026 (for backtesting)
```

Saves TSV files to `collect/` with per-feature occurrence and frequency data.

### 2. Backtest

Score actual draws to evaluate prediction quality:

```bash
python -m selma backtest                # score 2026 draws
python -m selma backtest 2025-01-01     # score from a different date
```

Uses weights from `results/weights.tsv` if available, otherwise defaults. Saves per-draw scores to `results/backtest.tsv`.

### 3. Optimize weights (optional)

Find optimal feature weights by maximizing scores of known draws:

```bash
python -m selma optimize                # optimize against 2026 draws
python -m selma optimize 2025-01-01     # optimize against a different period
```

Tests ~53K weight combinations (step 0.05) and saves the best to `results/weights.tsv`. Run backtest again afterwards to see the improvement.

### 4. Train model (optional)

Train a logistic regression model as an alternative to the weighted sum:

```bash
python -m selma train                   # train on data before 2026
python -m selma backtest-model          # score 2026 draws with the model
```

Saves model to `results/model.pkl` and coefficients to `results/model_coefficients.tsv`.

### 5. Predict

Generate and score all combinations:

```bash
python -m selma predict                 # score with weighted sum
python -m selma predict --model         # score with logistic regression model
```

Filters ~14M combinations (skips those with zero probability in any feature), scores the rest, and saves to `results/numbers.txt`.

### 6. Visualize

Generate the interactive HTML dashboard:

```bash
python -m selma visualize
```

Generates a multi-page static site in `docs/`, served via GitHub Pages at [riasc.github.io/SELMA](https://riasc.github.io/SELMA/).

## Automation

A GitHub Actions workflow automatically regenerates the visualization when `numbers/`, `selma/`, or `collect/` are updated on push. It runs `collect` and `visualize`, then commits the updated `docs/` and `collect/` back to the repo.

## Features

Each feature analyzes a structural property of lottery draws:

| Feature | Module | Description |
|---|---|---|
| **Odd/Even** | `oddeven.py` | Ratio of odd to even numbers (e.g., 3/3, 4/2) |
| **Templates** | `templates.py` | Decade group pattern (numbers mapped to groups 0-4) |
| **Sum Range** | `sumrange.py` | Sum of 6 numbers (typical range: 120-180) |
| **Consecutive** | `consecutive.py` | Adjacent number pairs (e.g., 12-13) |
| **Recency** | `distance.py` | Combined gaps since each number last appeared |
| **Hot/Cold** | `hotcold.py` | Per-number frequency across time windows |
| **Profiles** | `profiles.py` | Per-number yearly trajectory patterns |

## Scoring

Combinations are scored using a weighted sum of normalized feature probabilities:

```
score = w1 * norm(oddeven) + w2 * norm(start) + w3 * norm(template)
      + w4 * norm(sum) + w5 * norm(consec) + w6 * norm(recency)
```

Each probability is normalized to 0-1 by dividing by the maximum observed probability for that feature. Weights sum to 1.0 and can be optimized via `python -m selma optimize`. Alternatively, a logistic regression model can be trained via `python -m selma train`.

## Data Format

Historical draws in `numbers/YYYY.txt` (tab-separated):

```
Date    1    2    3    4    5    6    SZ
2024-01-03    14    25    28    32    36    49    4
```

- Columns 1-6: main numbers (1-49)
- SZ: Superzahl / bonus number (0-9, or -1 for older draws)
- Two draws per week (Wednesday and Saturday)