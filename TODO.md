# TODO

## Prediction pipeline rework
- [ ] Score & rank individual numbers (1-49) using composite of frequency, recency, trend
- [ ] Select top N candidates (e.g. 15-20) to reduce search space
- [ ] Generate combinations only from top N candidates
- [ ] Apply combination-level filters (odd/even, template, distance) as second pass
- [ ] Output final ranked predictions

## Number-level patterns
- [x] Hot/cold numbers: rolling window frequency (last 20/50/100 draws vs. overall)
- [x] Consecutive numbers: count consecutive pairs per draw, weight by historical frequency
- [x] Sum range: filter/weight combinations by historical sum frequency

## Pair/group analysis
- [~] Number pair frequency: skipped — too noisy with limited draws, mostly reflects individual frequency
- [x] Decade spread: covered by templates (group pattern already encodes decade distribution)

## Temporal patterns
- [x] Day-of-week bias: compare Wednesday vs. Saturday distributions (in hotcold)
- [x] Seasonal trends: per-year number frequency (in hotcold)

## Validation
- [ ] Backtesting: hold out last N draws, predict using prior data, measure ranking accuracy
