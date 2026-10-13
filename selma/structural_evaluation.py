"""Walk-forward comparison of SELMA combination scores against uniform draws."""
import argparse
from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import random
from statistics import mean

from selma.config import NUMBERS_DIR, RESULTS_DIR
from selma.consecutive import Consecutive
from selma.oddeven import OddEven
from selma.templates import Templates
from selma.evaluation import bootstrap_ci, load_draws

FEATURES = ('oddeven', 'start', 'template', 'sum', 'consec', 'recency')
# Fixed existing SELMA defaults; no fitting on the evaluation period.
WEIGHTS = (0.20, 0.10, 0.15, 0.20, 0.20, 0.15)


class History:
    def __init__(self, stats_from):
        self.stats_from = stats_from
        self.counts = [Counter() for _ in FEATURES]
        self.last_seen = {}
        self.index = 0
        self.training_draws = 0
        self.odd = OddEven.__new__(OddEven)
        self.templates = Templates.__new__(Templates)

    def keys(self, numbers):
        numbers = sorted(numbers)
        start, template = self.templates.getStartTemplate(numbers)
        gap = (sum(self.index - self.last_seen[n] for n in numbers)
               if all(n in self.last_seen for n in numbers) else None)
        return (self.odd.detOddEvenRatio(numbers), start, tuple(template),
                sum(numbers), Consecutive.count_pairs(numbers), gap)

    def observe(self, day, numbers):
        keys = self.keys(numbers)
        if day >= self.stats_from:
            for counts, key in zip(self.counts, keys):
                if key is not None:
                    counts[key] += 1
            self.training_draws += 1
        for number in numbers:
            self.last_seen[number] = self.index
        self.index += 1

    def scorer(self):
        # count / max(count) equals probability / max(probability).
        tables = [{key: count / max(counts.values()) for key, count in counts.items()}
                  for counts in self.counts]

        def score(numbers):
            keys = self.keys(numbers)
            features = tuple(table.get(key, 0.0) for table, key in zip(tables, keys))
            accepted = all(key in table for table, key in zip(tables[:5], keys[:5]))
            # Rejected combinations rank below every accepted combination.
            combined = sum(w * value for w, value in zip(WEIGHTS, features)) if accepted else -1.0
            return features + (combined,), accepted
        return score


def rank_result(actual, references):
    """Midrank percentile and fractional top-decile membership across tied ranks.

    Including the actual draw makes the rank comparison exchangeable under the
    null. Fractional membership is the expectation over uniform tie breaking.
    """
    lower = sum(value < actual for value in references)
    equal = sum(value == actual for value in references)
    size = len(references) + 1
    lo, hi = lower / size, (lower + equal + 1) / size
    return (lo + hi) / 2, max(0.0, hi - max(lo, 0.9)) / (hi - lo)


def evaluate_structural(draws, test_from='2026-01-01', stats_from='2000-01-01',
                        samples=10000, seed=42, repetitions=2000):
    if samples < 1:
        raise ValueError('samples must be positive')
    if stats_from >= test_from:
        raise ValueError('stats-from must precede test-from')
    history = History(stats_from)
    rows = []
    for day, numbers in draws:
        if day >= test_from:
            if history.training_draws < 100 or len(history.last_seen) != 49:
                raise ValueError('evaluation requires at least 100 prior frequency draws and all numbers seen')
            score = history.scorer()
            actual, accepted = score(numbers)
            digest = hashlib.sha256(f'{seed}:{day}:structural'.encode()).digest()
            rng = random.Random(int.from_bytes(digest, 'big'))
            references = [[] for _ in actual]
            accepted_count = 0
            for _ in range(samples):
                values, valid = score(rng.sample(range(1, 50), 6))
                accepted_count += valid
                for column, value in zip(references, values):
                    column.append(value)
            for name, value, reference in zip(FEATURES + ('combined',), actual, references):
                percentile, top10 = rank_result(value, reference)
                rows.append(dict(date=day, metric=name, numbers=' '.join(map(str, numbers)),
                                 training_draws=history.training_draws, score=value,
                                 percentile=percentile, top10_credit=top10,
                                 actual_accepted=accepted,
                                 random_accepted_fraction=accepted_count / samples))
        # Update only after scoring the current draw and all its controls.
        history.observe(day, numbers)
    if not rows:
        raise ValueError('no draws in evaluation period')
    summaries = {}
    for name in FEATURES + ('combined',):
        selected = [row for row in rows if row['metric'] == name]
        percentiles = [row['percentile'] for row in selected]
        top10 = [row['top10_credit'] for row in selected]
        summaries[name] = dict(mean_percentile=mean(percentiles),
                               mean_percentile_ci95=bootstrap_ci(percentiles, seed, repetitions),
                               top10_rate=mean(top10),
                               top10_rate_ci95=bootstrap_ci(top10, seed, repetitions))
    combined_rows = [row for row in rows if row['metric'] == 'combined']
    return dict(
        holdout_range=[rows[0]['date'], rows[-1]['date']], draws=len(combined_rows),
        stats_from=stats_from, random_combinations_per_draw=samples, seed=seed,
        weights=dict(zip(FEATURES, WEIGHTS)), metrics=summaries,
        actual_filtered=sum(not row['actual_accepted'] for row in combined_rows),
        random_filtered_fraction=mean(1 - row['random_accepted_fraction'] for row in combined_rows),
        bootstrap_repetitions=repetitions, bootstrap_block_draws=10,
        notes=[
            'Uses SELMA odd/even, start/template and consecutive helpers; normalized historical frequency scores.',
            'Fixed default weights, no optimization and no saved model or collected statistics loaded.',
            'Frequencies use stats-from <= date < current draw; recency history uses all prior draws.',
            'Recency date cutoff uses >= rather than the legacy exact-date lookup; source numbers are sorted.',
            'Combined score preserves hard filtering: unseen structural categories rank below accepted combinations.',
            'Individual metrics are evaluated without the other metrics hard filters; unseen values score zero.',
            'Controls are independent uniform six-number combinations sampled with replacement across combinations, without replacement within each combination.',
            'Midrank percentile accounts for ties. Top-10 credit averages uniform tie breaking across the boundary; it may be fractional.',
            'Chance expectations are 0.5 mean percentile and 0.1 top-10 rate.',
            'Paired-by-draw rank comparisons; 95% circular block bootstrap intervals, no multiple-testing adjustment.',
            'Combined fixed-default score is the primary comparison; individual metrics are exploratory.',
            'Historical evaluation reuses previously examined 2026 data; it is not a fresh prospective holdout.',
        ]), rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    iso = lambda value: date.fromisoformat(value).isoformat()
    parser.add_argument('--test-from', default='2026-01-01', type=iso)
    parser.add_argument('--stats-from', default='2000-01-01', type=iso)
    parser.add_argument('--samples', default=10000, type=int)
    parser.add_argument('--seed', default=42, type=int)
    parser.add_argument('--output', type=Path, default=Path(RESULTS_DIR) / 'structural_evaluation')
    args = parser.parse_args(argv)
    try:
        report, rows = evaluate_structural(load_draws(NUMBERS_DIR), args.test_from,
                                          args.stats_from, args.samples, args.seed)
    except ValueError as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    with (args.output / 'draws.tsv').open('w') as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    print(f"{report['draws']} draws; {args.samples:,} random controls per draw; fixed default weights")
    print('Metric       Mean percentile [95% CI]      Top-10% rate [95% CI]')
    for name, summary in report['metrics'].items():
        lo, hi = summary['mean_percentile_ci95']
        tl, th = summary['top10_rate_ci95']
        print(f"{name:<12} {summary['mean_percentile']:6.1%} [{lo:.1%}, {hi:.1%}]"
              f"          {summary['top10_rate']:.1%} [{tl:.1%}, {th:.1%}]")
    print('Chance: mean percentile 50%; top-10 rate 10%. Ties receive fractional credit.')
    print(f"Actual draws rejected by hard filters: {report['actual_filtered']}")
    print(f'Results: {args.output}')
