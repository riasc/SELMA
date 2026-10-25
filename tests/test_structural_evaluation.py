import ast
from datetime import date, timedelta
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from selma.consecutive import Consecutive
from selma.distance import DrawDistance
from selma.oddeven import OddEven
from selma.sumrange import SumRange
from selma.templates import Templates
from selma.structural_evaluation import History, WEIGHTS, evaluate_structural, rank_result


class Matrix:
    def __init__(self, rows):
        self.rows = rows
        self.shape = (len(rows), 6)

    def __getitem__(self, index):
        return self.rows[index]


class StructuralTests(unittest.TestCase):
    def setUp(self):
        rng = random.Random(8)
        self.draws = [((date(2020, 1, 1) + timedelta(days=i)).isoformat(),
                       tuple(sorted(rng.sample(range(1, 50), 6)))) for i in range(130)]

    def test_scores_match_existing_collectors(self):
        days, numbers = zip(*self.draws[:120])
        history = History(days[0])
        for day, combo in self.draws[:120]:
            history.observe(day, combo)
        collectors = []
        for cls in (OddEven, Templates, SumRange, Consecutive, DrawDistance):
            with patch.object(cls, '_save'):
                collectors.append(cls(Matrix(numbers), days, from_date=days[0]))
        odd, templates, sums, consecutive, distance = collectors
        tables = [odd.freq, templates.starts, templates.templates, sums.freq,
                  consecutive.freq, distance.distance]
        for _, combo in self.draws:
            expected = tuple(table.get(key, [0, 0])[1] / max(v[1] for v in table.values())
                             for table, key in zip(tables, history.keys(combo)))
            actual, accepted = history.scorer()(combo)
            for left, right in zip(actual[:6], expected):
                self.assertAlmostEqual(left, right)
            self.assertEqual(accepted, all(value > 0 for value in expected[:5]))
            self.assertAlmostEqual(actual[-1], sum(w * v for w, v in zip(WEIGHTS, expected))
                                   if accepted else -1)

    def test_weights_match_prediction_defaults(self):
        tree = ast.parse((Path(__file__).resolve().parent.parent / 'selma' / 'prediction.py').read_text())
        value = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'DEFAULT_WEIGHTS' for t in node.targets))
        self.assertEqual(tuple(ast.literal_eval(value)), WEIGHTS)

    def test_ties_have_correct_chance_expectations(self):
        self.assertAlmostEqual(rank_result(1, [1] * 99)[0], 0.5)
        self.assertAlmostEqual(rank_result(1, [1] * 99)[1], 0.1)
        values = [0] * 7 + [1] * 12 + [2]
        ranks = [rank_result(v, values[:i] + values[i + 1:]) for i, v in enumerate(values)]
        self.assertAlmostEqual(sum(r[0] for r in ranks) / len(ranks), 0.5)
        self.assertAlmostEqual(sum(r[1] for r in ranks) / len(ranks), 0.1)

    def test_current_and_future_outcomes_do_not_enter_reference_statistics(self):
        changed = [(day, numbers if i < 125 else (1, 2, 3, 4, 5, 6))
                   for i, (day, numbers) in enumerate(self.draws)]
        arguments = dict(test_from=self.draws[120][0], stats_from=self.draws[0][0],
                         samples=100, repetitions=30)
        _, original = evaluate_structural(self.draws, **arguments)
        _, altered = evaluate_structural(changed, **arguments)
        cutoff = self.draws[125][0]
        self.assertEqual([r for r in original if r['date'] < cutoff],
                         [r for r in altered if r['date'] < cutoff])
        self.assertEqual([r['random_accepted_fraction'] for r in original if r['date'] == cutoff],
                         [r['random_accepted_fraction'] for r in altered if r['date'] == cutoff])
        self.assertEqual(original[0]['training_draws'], 120)

    def test_date_cutoff_and_filtered_combination(self):
        history = History('2020-01-11')
        for day, numbers in self.draws[:20]:
            history.observe(day, numbers)
        self.assertEqual(history.training_draws, 10)
        self.assertEqual(sum(history.counts[0].values()), 10)
        history.counts[2].clear()
        scores, accepted = history.scorer()((1, 2, 3, 4, 5, 6))
        self.assertFalse(accepted)
        self.assertEqual(scores[-1], -1)


if __name__ == '__main__':
    unittest.main()
