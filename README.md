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

### 2. Evaluate SELMA's combination scores against chance

```bash
python -m selma evaluate-structural
python -m selma evaluate-structural --test-from 2026-01-01 --stats-from 2000-01-01 --samples 10000 --seed 42
```

Before each test draw, this command updates the historical frequency tables using
only earlier draws. It scores the actual six-number combination and 10,000
uniform random combinations using SELMA's odd/even, start-group, template, sum,
consecutive-pair, and recency metrics. It also evaluates their weighted sum with
the existing default weights (0.20, 0.10, 0.15, 0.20, 0.20, 0.15). No weights are
fitted and no saved model or collected statistics are loaded.

Feature scores use historical frequency divided by the highest frequency, just
as in prediction. The combined ranking preserves SELMA's hard filters: combinations
with unseen structural categories rank below every accepted combination. They
remain in the evaluation denominator. Individual metrics are tested independently
without the other metrics' filters. Recency remains a soft feature.

Frequency tables start at `--stats-from`; last-seen tracking uses all earlier
draws. Unlike the legacy distance collector's exact-date lookup, the cutoff is
applied as a date comparison even when no draw occurred on the cutoff date.
Input combinations are sorted. These corrections preserve the intended feature
definitions while making historical evaluation chronological.

The main outputs are the winning draw's mean percentile and its rate of appearing
in the highest-scoring 10%. Chance predicts **50% mean percentile** and **10%
top-decile rate**. Equal scores receive midrank percentiles and fractional
top-decile credit, equivalent to averaging random tie breaking. This matters for
coarse features such as odd/even. Random controls include all combinations, and
are sampled independently for each date with replacement between combinations.
The actual draw is included in the rank denominator for an exchangeable comparison.

`results/structural_evaluation/summary.json` records settings, metrics, filter
rates, and 95% circular block bootstrap intervals (2,000 resamples of 10-draw
blocks). `draws.tsv` records the dated actual scores and ranks. The fixed-weight
combined score is the primary comparison; individual metrics are exploratory,
with no multiple-comparison adjustment. This reuses previously inspected 2026
data and is a historical evaluation, not a new prospective holdout. It evaluates
the default weighted ranking, not the trained logistic regression model.

### Learn weights and test subsequent years

```bash
python -m selma evaluate-rolling
```

At the start of each year from 2016 onward, this experiment selects weights using
the preceding five calendar years. It maximizes the mean percentile of historical
winners against random combinations, then freezes those weights for the next
year. Every historical training example also uses only statistics available
before its draw. Feature tables continue updating after each observed draw;
weights change only at year boundaries.

The predefined search includes 126 nonnegative weight combinations in steps of
0.25, summing to one, plus the existing default weights. Exact ties favor defaults.
It uses 128 random controls per training draw and 2,000 independent controls per
test draw. Learned and default scores share test controls for a paired comparison.
SELMA's hard filters apply to every candidate, even when a feature has zero weight.
The search is finite and does not establish whether other models could work.

Settings can be changed using `--start-year`, `--train-years`, `--stats-from`,
`--train-samples`, `--test-samples`, and `--seed`. Changing these after looking at
results turns them into additional exploratory experiments.

`results/rolling_evaluation/summary.json` includes each year's selected weights,
training rank, subsequent performance, and aggregate comparisons with defaults
and chance. `draws.tsv` contains each dated test result. The 95% intervals use
2,000 circular block bootstrap samples with 10-draw blocks; they are descriptive,
since shared yearly weights can create longer dependencies. This historical
experiment includes previously inspected 2026 data, not a prospective test.

### Number-level evaluation

```bash
python -m selma evaluate
python -m selma evaluate --tune-from 2016-01-01 --test-from 2026-01-01 --seed 42
```

This standard-library-only command uses strictly earlier draws for every forecast.
It compares uniform selection, smoothed historical frequency, recent frequency
(20/50/100 draws), cold numbers (50 draws), and a gap-rank recency heuristic.
All methods retain positive inclusion probabilities for all 49 numbers, summing
to six. Frequency estimates use 20 uniform pseudo-draws. Recency favors longer
gaps as an experimental hypothesis, not an assumption that numbers are due.

With at least 100 earlier draws required, the default tuning period is 2016–2025.
Each method's strength relative to uniform is chosen from 0, 0.1, 0.25, 0.5, and 1
by tuning-period Brier score. The best method is selected before scoring 2026.
Strength zero reduces a method to uniform. Parameters stay fixed during holdout;
history updates after each observed draw.

Outputs in `results/evaluation/`:

- `summary.json`: tuning selection, holdout scores, and paired 95% circular block
  bootstrap intervals (1,000 resamples, blocks of 10 draws).
- `draws.tsv`: dated probabilities, actual numbers, one ticket per strategy,
  matches, Brier score, and marginal log loss.

Lower Brier/log loss is better. Reported Brier gain is uniform minus strategy.
These are **per-number inclusion scores**, not probabilities of winning a jackpot.
Tickets choose the six highest probabilities, with reproducible random tie breaks;
uniform therefore produces a random ticket. A random ticket averages 36/49
(about 0.735) matches. Match intervals compare against the same realized random
baseline; intervals are not corrected for multiple comparisons. Only the method
selected on tuning is the primary comparison; the others are exploratory.

The command also evaluates **top-20 coverage**: before each holdout draw, take
each method's 20 highest-ranked numbers and count how many of the six winners
they contain. This uses the underlying ranking before strength mixing, so a
method tuned to zero strength still has its original ranking tested. Ties use
the same seeded random ordering as tickets. Random groups capture 120/49
(about 2.449) winners per draw on average. The report includes coverage, counts
for 0–6 captured winners, and bootstrap intervals for gains against both that
exact expectation and a realized random group. The exact random coverage
distribution is hypergeometric: `C(20,k) * C(29,6-k) / C(49,6)`.
The dated groups and their matches are saved in `draws.tsv`. This additional
metric was introduced after inspecting the original holdout and is exploratory;
no new method selection is made from its holdout results.

This is a historical holdout, not a prospective trial. Repeatedly adjusting models
after inspecting its results makes it unsuitable as an untouched test. Superzahl,
payouts, and ticket costs are not evaluated. Run checks with
`python -m unittest discover -s tests -v`.

### Legacy score inspection

Score actual draws using the original structural ranking:

```bash
python -m selma backtest                # score 2026 draws
python -m selma backtest 2025-01-01     # score from a different date
```

Uses weights from `results/weights.tsv` if available, otherwise defaults. Saves per-draw scores to `results/backtest.tsv`.

This legacy command does not compare against chance or enforce chronological
feature construction. Its scores alone do not establish predictive performance.

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

A second workflow (`fetch-draws.yml`) runs daily, downloads the official WestLotto CSV archives, reconciles `numbers/` with them via `selma.audit_archive --apply`, and opens or updates a single `data` pull request on the `data/auto-draws` branch when new or corrected draws exist. Merging that PR triggers the visualization update as usual.

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

The archive was reconciled on October 8, 2026 against official WestLotto CSV
downloads linked by [LOTTO Thüringen](https://www.lotto-thueringen.de/service/downloads/downloads.html).
It contains 5,053 draws through October 7, 2026. Repairs added 55 missing draws
(five in 2020 and 50 in 2021), corrected three dates, one main-number entry and
one Superzahl. A missing 2021 header had also caused the old loader to skip a
valid draw. Both evaluation and collection now share a validated loader that
accepts headerless files and rejects duplicate dates or invalid numbers.

The historical scope is the original weekend series through December 2, 2000,
then the unified Wednesday/Saturday series. Earlier separate Wednesday games
(7/38 and A/B 6/49) are excluded. The unified series has no scheduled-date gaps
through the audit cutoff. Current official CSV dates take precedence over date
disagreements in the older Excel archive.

To repeat the comparison using downloaded official CSV ZIP files:

```bash
python3 -m selma.audit_archive --official-zip historic.zip --official-zip current.zip --through 2026-10-07 --output results/archive_audit/check
```

This is a dry run; add `--apply` to repair files with backups in the output
directory. Exact download URLs, source hashes, all corrections, repaired file
hashes and before/after experiment summaries are in
[`audit/2026-10-08.json`](audit/2026-10-08.json).

All three evaluations were rerun with their previous settings after repair.
The rolling experiment now covers 1,124 draws from 2016–2026, selecting among
127 weight settings using the preceding five years and freezing weights for
each test year. Learned weights achieved a mean winning-combination percentile
of **50.98%** (95% block-bootstrap interval **49.20–52.65%**), versus **51.56%**
for default weights and **50%** expected by chance. Learned top-10% capture was
**11.67%** (interval **9.81–13.52%**), versus **10%** by chance. Neither primary
result establishes an advantage. Some exploratory individual metrics have
nominal intervals excluding chance; these do not account for multiple testing.
This rerun reuses examined historical data, so it is not fresh prospective
validation. Collected statistics and the local dashboard were regenerated;
saved prediction models and exhaustive combination scores were not retrained.

Historical draws in `numbers/YYYY.txt` (tab-separated):

```
Date    1    2    3    4    5    6    SZ
2024-01-03    14    25    28    32    36    49    4
```

- Columns 1-6: main numbers (1-49)
- SZ: Superzahl / bonus number (0-9, or -1 for older draws)
- Two draws per week (Wednesday and Saturday)
