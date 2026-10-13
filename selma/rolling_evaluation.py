"""Learn SELMA weights on earlier years and evaluate the following year."""
import argparse
from collections import deque
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import random
from statistics import mean

from selma.config import NUMBERS_DIR, RESULTS_DIR
from selma.evaluation import bootstrap_ci, load_draws
from selma.structural_evaluation import FEATURES, WEIGHTS, History, rank_result


def candidate_weights():
    """Fixed quarter-step simplex grid plus SELMA defaults (127 candidates)."""
    candidates = [WEIGHTS]

    def visit(remaining, values):
        if len(values) == 5:
            candidates.append(tuple(v / 4 for v in values + [remaining]))
        else:
            for value in range(remaining + 1):
                visit(remaining - value, values + [value])
    visit(4, [])
    return candidates


def rng_for(seed, day, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(f'{seed}:{day}:{purpose}'.encode()).digest(), 'big'))


def weighted(features, accepted, weights):
    return sum(w * f for w, f in zip(weights, features)) if accepted else -1.0


def controls(score, count, rng):
    return [score(rng.sample(range(1, 50), 6)) for _ in range(count)]


def compare(actual, references, weights):
    values, accepted = actual
    return rank_result(weighted(values, accepted, weights),
                       [weighted(f, valid, weights) for f, valid in references])


def choose(training, candidates):
    means = [mean(row[1][i] for row in training) for i in range(len(candidates))]
    # Candidate zero is the default, so exact ties favor it.
    best = max(range(len(candidates)), key=lambda i: means[i])
    return best, means[best], means[0]


def summarize(rows, seed, repetitions):
    result = {'draws': len(rows)}
    for method in ('learned', 'default'):
        for metric in ('percentile', 'top10'):
            values = [r[f'{method}_{metric}'] for r in rows]
            result[f'{method}_{metric}'] = mean(values)
            result[f'{method}_{metric}_ci95'] = bootstrap_ci(values, seed, repetitions)
    for metric in ('percentile', 'top10'):
        deltas = [r[f'learned_{metric}'] - r[f'default_{metric}'] for r in rows]
        result[f'{metric}_gain'] = mean(deltas)
        result[f'{metric}_gain_ci95'] = bootstrap_ci(deltas, seed, repetitions)
    return result


def evaluate_rolling(draws, start_year=2016, train_years=5, stats_from='2000-01-01',
                     train_samples=128, test_samples=2000, seed=42, repetitions=2000,
                     progress=None):
    if train_years < 1 or min(train_samples, test_samples, repetitions) < 1:
        raise ValueError('window, samples, and repetitions must be positive')
    first_training = f'{start_year - train_years:04d}-01-01'
    if stats_from >= first_training:
        raise ValueError('stats-from must precede the first training year')
    candidates = candidate_weights()
    history = History(stats_from)
    training = deque()
    rows, years = [], []
    active_year = None
    for day, numbers in draws:
        if day < first_training:
            history.observe(day, numbers)
            continue
        if history.training_draws < 100 or len(history.last_seen) != 49:
            raise ValueError('at least 100 prior statistics draws and all numbers seen are required')
        year = int(day[:4])
        if year >= start_year and year != active_year:
            cutoff = f'{year - train_years:04d}-01-01'
            while training and training[0][0] < cutoff:
                training.popleft()
            if len(training) < 100:
                raise ValueError('at least 100 training draws are required for each test year')
            selected, training_rank, default_training_rank = choose(training, candidates)
            active_year = year
            years.append(dict(year=year, training_from=training[0][0], training_to=training[-1][0],
                              training_draws=len(training), weights=dict(zip(FEATURES, candidates[selected])),
                              training_percentile=training_rank, default_training_percentile=default_training_rank))
            if progress:
                progress(f'{year}: weights {candidates[selected]}, training rank {training_rank:.1%}')
        score = history.scorer()
        actual = score(numbers)
        if year >= start_year:
            reference = controls(score, test_samples, rng_for(seed, day, 'rolling-test'))
            learned = compare(actual, reference, candidates[selected])
            default = compare(actual, reference, WEIGHTS)
            rows.append(dict(date=day, year=year, learned_percentile=learned[0], default_percentile=default[0],
                             learned_top10=learned[1], default_top10=default[1],
                             actual_accepted=actual[1], numbers=' '.join(map(str, numbers))))
        reference = controls(score, train_samples, rng_for(seed, day, 'rolling-training'))
        training.append((day, [compare(actual, reference, weights)[0] for weights in candidates]))
        history.observe(day, numbers)
    if not rows:
        raise ValueError('no test draws')
    for record in years:
        record.update(summarize([r for r in rows if r['year'] == record['year']], seed, repetitions))
    report = dict(test_range=[rows[0]['date'], rows[-1]['date']], start_year=start_year,
                  train_years=train_years, stats_from=stats_from, train_samples=train_samples,
                  test_samples=test_samples, seed=seed, candidate_count=len(candidates),
                  bootstrap_repetitions=repetitions, bootstrap_block_draws=10,
                  aggregate=summarize(rows, seed, repetitions), years=years,
                  notes=[
                      'Weights selected by mean training midrank against uniform random combinations, not absolute scores.',
                      'Fixed nonnegative quarter-step weights summing to one plus defaults. No search choices tuned on test results.',
                      'Each January selects using only previous train-years calendar years; weights stay fixed for the entire test year.',
                      'Frequency tables update before every draw from strictly earlier draws; training features also use strictly prior history.',
                      'Training controls and test controls use independent deterministic random streams; learned and default weights share test controls.',
                      'Hard filters retained for all candidates, including zero-weight features; rejected combinations rank below accepted ones.',
                      'Midranks and fractional top-decile membership handle ties. Chance baselines: 50% and 10%.',
                      '95% circular 10-draw block bootstrap intervals are descriptive; annual weight fitting can induce longer dependence.',
                      'Historical rolling evaluation, including previously examined 2026 data; not a prospective confirmation.',
                      'This is a finite grid search, not a proof that no other weights or models can work.',
                  ])
    return report, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-year', type=int, default=2016)
    parser.add_argument('--train-years', type=int, default=5)
    parser.add_argument('--stats-from', type=lambda x: date.fromisoformat(x).isoformat(), default='2000-01-01')
    parser.add_argument('--train-samples', type=int, default=128)
    parser.add_argument('--test-samples', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path(RESULTS_DIR) / 'rolling_evaluation')
    args = parser.parse_args(argv)
    try:
        report, rows = evaluate_rolling(load_draws(NUMBERS_DIR), args.start_year, args.train_years,
                                       args.stats_from, args.train_samples, args.test_samples, args.seed,
                                       progress=lambda message: print(message, flush=True))
    except ValueError as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    with (args.output / 'draws.tsv').open('w') as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    print('Year   Draws   Learned rank   Default rank   Learned top10   Default top10')
    for row in report['years']:
        print(f"{row['year']}   {row['draws']:4}    {row['learned_percentile']:.1%}          "
              f"{row['default_percentile']:.1%}          {row['learned_top10']:.1%}           {row['default_top10']:.1%}")
    print(json.dumps(report['aggregate'], indent=2))
    print(f'Results: {args.output}')
