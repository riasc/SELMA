"""Chronological evaluation of main-number marginals; standard library only."""
import argparse
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import mean

from selma.config import NUMBERS_DIR, RESULTS_DIR

BASE = 6 / 49
METHODS = ('uniform', 'frequency', 'hot20', 'hot50', 'hot100', 'cold50', 'recency')
STRENGTHS = (0.0, 0.1, 0.25, 0.5, 1.0)


def load_draws(directory):
    """Read validated records, including headerless files, through the shared loader."""
    from selma.archive import load_records
    return [(day, numbers) for day, numbers, _ in load_records(directory)]


def forecasts(history):
    """Each vector contains inclusion probabilities summing to six."""
    def frequency(rows):
        counts = [0] * 49
        for _, numbers in rows:
            for number in numbers:
                counts[number - 1] += 1
        # Twenty uniform pseudo-draws keep every valid number possible.
        return [(count + 20 * BASE) / (len(rows) + 20) for count in counts]

    result = {'uniform': [BASE] * 49, 'frequency': frequency(history)}
    for window in (20, 50, 100):
        result[f'hot{window}'] = frequency(history[-window:])
    result['cold50'] = [(1 - p) * 6 / 43 for p in result['hot50']]
    last_seen = [-1] * 49
    for index, (_, numbers) in enumerate(history):
        for number in numbers:
            last_seen[number - 1] = index
    gaps = [len(history) - index for index in last_seen]
    # Average ranks preserve ties and sum to 49 * 24.
    ranks = [sum(other < gap for other in gaps)
             + (sum(other == gap for other in gaps) - 1) / 2 for gap in gaps]
    result['recency'] = [BASE * (1 + 0.9 * (rank / 24 - 1)) for rank in ranks]
    return result


def mix(probabilities, strength):
    return [BASE + strength * (p - BASE) for p in probabilities]


def metrics(probabilities, numbers):
    actual = set(numbers)
    targets = [int(number in actual) for number in range(1, 50)]
    brier = mean((p - y) ** 2 for p, y in zip(probabilities, targets))
    loss = -mean(y * math.log(p) + (1 - y) * math.log1p(-p)
                 for p, y in zip(probabilities, targets))
    return brier, loss


def ticket(probabilities, day, seed, size=6):
    """Top-ranked group; deterministic random tie breaks shared across methods."""
    if not 1 <= size <= 49:
        raise ValueError('group size must be between 1 and 49')
    digest = hashlib.sha256(f'{seed}:{day}'.encode()).digest()
    rng = random.Random(int.from_bytes(digest, 'big'))
    ties = [rng.random() for _ in range(49)]
    return sorted(sorted(range(1, 50),
                         key=lambda n: (probabilities[n - 1], ties[n - 1]),
                         reverse=True)[:size])


def bootstrap_ci(values, seed, repetitions=1000, block=10):
    """Paired circular block bootstrap over draw-level differences."""
    rng = random.Random(seed)
    n = len(values)
    block = max(1, min(block, n // 2))  # keep resamples varied when n is small
    estimates = []
    for _ in range(repetitions):
        sample = []
        while len(sample) < n:
            start = rng.randrange(n)
            sample.extend(values[(start + offset) % n] for offset in range(block))
        estimates.append(mean(sample[:n]))
    estimates.sort()
    return [estimates[int(repetitions * 0.025)], estimates[int(repetitions * 0.975)]]


def evaluate(draws, tune_from='2016-01-01', test_from='2026-01-01', seed=42,
             min_history=100, repetitions=1000):
    if tune_from >= test_from:
        raise ValueError('tune-from must precede test-from')
    tuning = []
    holdout = []
    for index, (day, numbers) in enumerate(draws):
        if index < min_history or day < tune_from:
            continue
        row = (day, numbers, forecasts(draws[:index]))
        (tuning if day < test_from else holdout).append(row)
    if not tuning or not holdout:
        raise ValueError('both tuning and holdout need draws after the warm-up')

    strengths = {}
    tuning_scores = {}
    for method in METHODS:
        choices = (0.0,) if method == 'uniform' else STRENGTHS
        candidates = [(mean(metrics(mix(f[method], strength), numbers)[0]
                            for _, numbers, f in tuning), strength)
                      for strength in choices]
        score, strengths[method] = min(candidates)
        tuning_scores[method] = score
    # Selection is complete before any holdout outcome is evaluated.
    selected = min(METHODS, key=lambda method: tuning_scores[method])
    rows = []
    for day, numbers, forecast in holdout:
        for method in METHODS:
            probabilities = mix(forecast[method], strengths[method])
            brier, loss = metrics(probabilities, numbers)
            chosen = ticket(probabilities, day, seed)
            # Assess the underlying ranking even when Brier tuning chose uniform.
            top20 = ticket(forecast[method], day, seed, size=20)
            rows.append(dict(date=day, method=method, strength=strengths[method],
                             brier=brier, marginal_log_loss=loss,
                             matches=len(set(chosen) & set(numbers)),
                             ticket=' '.join(map(str, chosen)),
                             top20=' '.join(map(str, top20)),
                             top20_matches=len(set(top20) & set(numbers)),
                             actual=' '.join(map(str, numbers)),
                             probabilities=probabilities))
    baseline = [row for row in rows if row['method'] == 'uniform']
    summaries = {}
    for method in METHODS:
        samples = [row for row in rows if row['method'] == method]
        improvements = [b['brier'] - r['brier'] for b, r in zip(baseline, samples)]
        match_deltas = [r['matches'] - b['matches'] for b, r in zip(baseline, samples)]
        coverage = [r['top20_matches'] for r in samples]
        coverage_deltas = [r['top20_matches'] - b['top20_matches']
                           for b, r in zip(baseline, samples)]
        chance_deltas = [value - 120 / 49 for value in coverage]
        summaries[method] = dict(
            strength=strengths[method], tuning_brier=tuning_scores[method],
            brier=mean(r['brier'] for r in samples),
            marginal_log_loss=mean(r['marginal_log_loss'] for r in samples),
            brier_improvement=mean(improvements),
            brier_improvement_ci95=bootstrap_ci(improvements, seed, repetitions),
            mean_matches=mean(r['matches'] for r in samples),
            match_improvement=mean(match_deltas),
            match_improvement_ci95=bootstrap_ci(match_deltas, seed, repetitions),
            match_counts={str(k): sum(r['matches'] == k for r in samples) for k in range(7)},
            top20_mean_matches=mean(coverage),
            top20_capture_fraction=mean(coverage) / 6,
            top20_gain_over_chance=mean(chance_deltas),
            top20_gain_over_chance_ci95=bootstrap_ci(chance_deltas, seed, repetitions),
            top20_gain_over_random_group=mean(coverage_deltas),
            top20_gain_over_random_group_ci95=bootstrap_ci(coverage_deltas, seed, repetitions),
            top20_match_counts={str(k): coverage.count(k) for k in range(7)})
    report = dict(
        tuning_range=[tuning[0][0], tuning[-1][0]], tuning_draws=len(tuning),
        holdout_range=[holdout[0][0], holdout[-1][0]], holdout_draws=len(holdout),
        selected_on_tuning=selected, seed=seed, min_history=min_history,
        bootstrap_repetitions=repetitions, bootstrap_block_draws=10,
        random_expected_matches=36 / 49, methods=summaries,
        top20_random_expected_matches=120 / 49,
        top20_random_match_probabilities={str(k): math.comb(20, k) * math.comb(29, 6 - k)
                                         / math.comb(49, 6) for k in range(7)},
        notes=[
            'Main numbers only; Brier and log loss score marginal inclusion probabilities, not jackpot probabilities.',
            'One ticket per method per draw. A zero strength produces the uniform ticket.',
            'Strength and method selection use tuning only. Holdout history updates after each observed draw.',
            'Intervals are paired circular block bootstrap estimates, not adjusted for multiple comparisons.',
            'Only the tuning-selected method is the primary comparison; other holdout comparisons are exploratory.',
            'Historical holdout is not a prospective test. Repeated tuning after viewing it invalidates its role.',
            'Top-20 is an exploratory coverage test added after inspecting the original holdout results.',
            'Top-20 uses each underlying unshrunk ranking, including methods whose Brier strength is zero; no method is selected on top-20 holdout performance.',
        ])
    return report, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tune-from', default='2016-01-01', type=lambda x: date.fromisoformat(x).isoformat())
    parser.add_argument('--test-from', default='2026-01-01', type=lambda x: date.fromisoformat(x).isoformat())
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path(RESULTS_DIR) / 'evaluation')
    args = parser.parse_args(argv)
    try:
        report, rows = evaluate(load_draws(NUMBERS_DIR), args.tune_from, args.test_from, args.seed)
    except ValueError as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    with (args.output / 'draws.tsv').open('w') as target:
        fields = list(rows[0])
        writer = csv.DictWriter(target, fieldnames=fields, delimiter='\t')
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, 'probabilities': json.dumps(row['probabilities'])})
    print(f"Tuning: {report['tuning_draws']} draws; holdout: {report['holdout_draws']} draws")
    print(f"Selected using tuning only: {report['selected_on_tuning']}")
    print('Method       Strength   Brier gain [95% interval]             Matches/ticket')
    for method, summary in report['methods'].items():
        low, high = summary['brier_improvement_ci95']
        print(f"{method:<12} {summary['strength']:>6.2f}     "
              f"{summary['brier_improvement']:+.6f} [{low:+.6f}, {high:+.6f}]"
              f"    {summary['mean_matches']:.3f}")
    print('Positive Brier gain favors the method. Random expected matches: 0.735.')
    print('Intervals are exploratory except for the tuning-selected comparison.')
    print('\nExploratory top-20 coverage (underlying rankings, before strength mixing):')
    print('Method       Captured/draw   Gain over chance [95% interval]    All six')
    for method, summary in report['methods'].items():
        low, high = summary['top20_gain_over_chance_ci95']
        print(f"{method:<12} {summary['top20_mean_matches']:>6.3f}          "
              f"{summary['top20_gain_over_chance']:+.3f} [{low:+.3f}, {high:+.3f}]"
              f"         {summary['top20_match_counts']['6']}")
    print('Chance expectation: 120/49 = 2.449 winning numbers in a group of 20.')
    print(f'Results: {args.output}')
