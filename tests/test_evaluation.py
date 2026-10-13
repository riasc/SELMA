import random
import tempfile
from pathlib import Path
import unittest
from datetime import date, timedelta

from selma.evaluation import BASE, evaluate, forecasts, load_draws, metrics, ticket


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        rng = random.Random(123)
        self.draws = [((date(2020, 1, 1) + timedelta(days=i)).isoformat(),
                       tuple(sorted(rng.sample(range(1, 50), 6)))) for i in range(160)]

    def run_evaluation(self, draws):
        return evaluate(draws, '2020-02-01', '2020-04-01', min_history=20, repetitions=50)

    def test_probabilities_are_valid(self):
        for history in ([], self.draws[:1], self.draws):
            for probabilities in forecasts(history).values():
                self.assertAlmostEqual(sum(probabilities), 6)
                self.assertTrue(all(0 < p < 1 for p in probabilities))

    def test_future_outcomes_cannot_change_past_predictions_or_selection(self):
        original_report, original_rows = self.run_evaluation(self.draws)
        changed = [(day, numbers if i < 120 else (1, 2, 3, 4, 5, 6))
                   for i, (day, numbers) in enumerate(self.draws)]
        changed_report, changed_rows = self.run_evaluation(changed)
        self.assertEqual(original_report['selected_on_tuning'], changed_report['selected_on_tuning'])
        for method in original_report['methods']:
            self.assertEqual(original_report['methods'][method]['strength'],
                             changed_report['methods'][method]['strength'])
        cutoff = self.draws[120][0]
        self.assertEqual([r for r in original_rows if r['date'] < cutoff],
                         [r for r in changed_rows if r['date'] < cutoff])
        self.assertEqual([r['probabilities'] for r in original_rows if r['date'] == cutoff],
                         [r['probabilities'] for r in changed_rows if r['date'] == cutoff])
        self.assertEqual([r['top20'] for r in original_rows if r['date'] == cutoff],
                         [r['top20'] for r in changed_rows if r['date'] == cutoff])

    def test_top20_coverage_and_chance_distribution(self):
        report, rows = self.run_evaluation(self.draws)
        for row in rows:
            group = set(map(int, row['top20'].split()))
            actual = set(map(int, row['actual'].split()))
            self.assertEqual(len(group), 20)
            self.assertEqual(row['top20_matches'], len(group & actual))
        distribution = report['top20_random_match_probabilities']
        self.assertAlmostEqual(sum(distribution.values()), 1)
        self.assertAlmostEqual(sum(int(k) * p for k, p in distribution.items()), 120 / 49)
        for summary in report['methods'].values():
            self.assertEqual(sum(summary['top20_match_counts'].values()), report['holdout_draws'])

    def test_top20_selects_highest_probabilities(self):
        probabilities = [n / 100 for n in range(49)]
        self.assertEqual(ticket(probabilities, '2026-01-01', 42, size=20), list(range(30, 50)))
        with self.assertRaises(ValueError):
            ticket(probabilities, '2026-01-01', 42, size=50)

    def test_uniform_score_and_ticket(self):
        probabilities = [BASE] * 49
        self.assertAlmostEqual(metrics(probabilities, (1, 2, 3, 4, 5, 6))[0], BASE * (1 - BASE))
        chosen = ticket(probabilities, '2026-01-01', 42)
        self.assertEqual(chosen, ticket(probabilities, '2026-01-01', 42))
        self.assertEqual(len(set(chosen)), 6)

    def test_loader_is_repeatable_sorts_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '2020.txt'
            path.write_text('Date\t1\t2\t3\t4\t5\t6\tSZ\n2020-01-01\t6\t5\t4\t3\t2\t1\t0\n')
            self.assertEqual(load_draws(directory), [('2020-01-01', (1, 2, 3, 4, 5, 6))])
            self.assertEqual(load_draws(directory), load_draws(directory))
            path.write_text(path.read_text() + '2020-01-01\t1\t2\t3\t4\t5\t6\t0\n')
            with self.assertRaisesRegex(ValueError, 'duplicate date'):
                load_draws(directory)

    def test_empty_holdout_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'both tuning and holdout'):
            evaluate(self.draws, '2020-02-01', '2026-01-01')


if __name__ == '__main__':
    unittest.main()
