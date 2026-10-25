from datetime import date, timedelta
import random
import unittest
from unittest.mock import patch

from selma.rolling_evaluation import candidate_weights, choose, compare, evaluate_rolling, weighted
from selma.structural_evaluation import WEIGHTS


class RollingTests(unittest.TestCase):
    def test_grid_is_fixed_valid_and_includes_defaults(self):
        candidates = candidate_weights()
        self.assertEqual(len(candidates), 127)
        self.assertEqual(len(set(candidates)), 127)
        self.assertEqual(candidates[0], WEIGHTS)
        for weights in candidates:
            self.assertAlmostEqual(sum(weights), 1)
            self.assertTrue(all(w >= 0 for w in weights))

    def test_optimization_uses_relative_rank(self):
        candidates = [(1, 0, 0, 0, 0, 0), (0, 1, 0, 0, 0, 0)]
        actual = ((0.9, 0.2, 0, 0, 0, 0), True)
        references = [((1, 0.1, 0, 0, 0, 0), True)] * 10
        ranks = [compare(actual, references, w)[0] for w in candidates]
        selected, _, _ = choose([('2020-01-01', ranks)], candidates)
        self.assertEqual(selected, 1)  # Lower absolute score, higher relative rank.
        self.assertEqual(weighted(actual[0], False, candidates[0]), -1)

    def test_year_weights_and_predictions_do_not_use_future_draws(self):
        rng = random.Random(7)
        draws = []
        for year in range(2018, 2022):
            count = 110 if year < 2021 else 8
            for i in range(count):
                day = (date(year, 1, 1) + timedelta(days=i)).isoformat()
                draws.append((day, tuple(sorted(rng.sample(range(1, 50), 6)))))
        altered = [(day, (1, 2, 3, 4, 5, 6) if day >= '2020-01-05' else combo)
                   for day, combo in draws]
        kwargs = dict(start_year=2020, train_years=1, stats_from='2018-01-01',
                      train_samples=4, test_samples=10, repetitions=20)
        with patch('selma.rolling_evaluation.candidate_weights', return_value=[WEIGHTS, (1, 0, 0, 0, 0, 0)]):
            report, rows = evaluate_rolling(draws, **kwargs)
            changed, other = evaluate_rolling(altered, **kwargs)
        self.assertEqual(report['years'][0]['weights'], changed['years'][0]['weights'])
        self.assertEqual(report['years'][0]['training_to'], '2019-04-20')
        self.assertEqual([r for r in rows if r['date'] < '2020-01-05'],
                         [r for r in other if r['date'] < '2020-01-05'])
        self.assertEqual(report['aggregate']['draws'], 118)
        self.assertTrue(all(record['training_to'] < f"{record['year']}-01-01" for record in report['years']))


if __name__ == '__main__':
    unittest.main()
