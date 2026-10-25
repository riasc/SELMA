# TODO

## Open
- [ ] Show the evaluation-versus-chance results on the dashboard (`visualize.py`)
- [ ] Optional polish from the PR #5 review: `@staticmethod` for `detOddEvenRatio`/`getStartTemplate`, top-level import in `evaluation.py`, drop unused `self.numbers` in `data.py`, dict dispatch in `__main__.py`
- [ ] Move the README headline results out of the Data Format section

## Dropped
- [~] Prediction pipeline rework (rank numbers → top-N candidates → combinations → filters): the chronological evaluations (PR #5) show no predictive signal in any feature, so a narrower search space cannot help. SELMA stays an analysis and evaluation tool.
- [~] Number pair frequency: too noisy with limited draws, mostly reflects individual frequency

## Done
- [x] Hot/cold numbers: rolling window frequency (last 20/50/100 draws vs. overall)
- [x] Consecutive numbers: count consecutive pairs per draw, weight by historical frequency
- [x] Sum range: filter/weight combinations by historical sum frequency
- [x] Decade spread: covered by templates
- [x] Day-of-week and per-year frequency (in hotcold)
- [x] Walk-forward number-level evaluation against uniform chance (`python -m selma evaluate`)
- [x] Walk-forward structural-score evaluation against random combinations (`python -m selma evaluate-structural`)
- [x] Rolling yearly weight learning, 2016–2026, against chance and default weights (`python -m selma evaluate-rolling`)
- [x] Archive audit and repair against official WestLotto CSV (`python -m selma.audit_archive`)
