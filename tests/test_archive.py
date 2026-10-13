import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from selma.archive import HEADER, load_records, schedule_gaps
from selma.audit_archive import differences, read_official, run
from selma.evaluation import load_draws


class ArchiveTests(unittest.TestCase):
    def test_headerless_first_record_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '2021.txt'
            path.write_text('2021-01-02\t34\t30\t28\t16\t8\t7\t6\n')
            self.assertEqual(load_draws(directory), [('2021-01-02', (7, 8, 16, 28, 30, 34))])
            path.write_text(HEADER + '\n' + path.read_text())
            self.assertEqual(len(load_records(directory)), 1)

    def test_rejects_bad_year_bonus_and_duplicate_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '2021.txt'
            for line in ('2020-01-02\t1\t2\t3\t4\t5\t6\t0',
                         '2021-01-02\t1\t2\t3\t4\t5\t6\t10',
                         '2021-01-02\t1\t2\t3\t4\t5\t5\t0'):
                path.write_text(line)
                with self.assertRaises(ValueError):
                    load_records(directory)

    def test_schedule_checks_unified_series_only(self):
        rows = [('1982-01-02', (), -1), ('2021-01-02', (), 0), ('2021-01-09', (), 0)]
        gaps = schedule_gaps(rows, '2021-01-09')
        self.assertIn('2021-01-06', gaps['missing_dates'])
        self.assertFalse(any(d < '2000-12-06' for d in gaps['missing_dates']))

    def test_rejects_unexplained_deletion(self):
        with self.assertRaisesRegex(ValueError, 'cannot be safely reconciled'):
            differences([('2021-01-02', (1, 2, 3, 4, 5, 6), 0)], [])

    def test_official_import_repair_and_second_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            numbers = root / 'numbers'
            numbers.mkdir()
            (numbers / '2021.txt').write_text('2021-01-02\t7\t8\t16\t28\t30\t34\t5\n')
            source = root / 'official.zip'
            # Main numbers are extraction order; SZ is column 10, not 8 or 9.
            text = ('Datum; ;Gewinnzahlen\n'
                    '28.04.1982; ;18;12;1;21;17;20;36;24; \n'
                    '04.06.1986;A;1;2;3;4;5;6;--;10; \n'
                    '02.01.2021; ;34;30;28;16;8;7;--;--;6\n'
                    '06.01.2021; ;44;38;37;32;21;14;--;--;6\n')
            with ZipFile(source, 'w') as archive:
                archive.writestr('LOTTO_ab_2021.csv', text)
            rows, _, excluded = read_official([source], '2021-01-06')
            self.assertEqual(len(rows), 2)
            self.assertEqual(sum(excluded.values()), 2)
            preview = run(numbers, [source], '2021-01-06', root / 'preview')
            self.assertFalse(preview['applied'])
            self.assertEqual(len(load_records(numbers)), 1)
            repaired = run(numbers, [source], '2021-01-06', root / 'repair', apply=True)
            self.assertEqual(repaired['after_count'], 2)
            self.assertEqual(repaired['change_counts'], {'missing_draw': 1, 'result_correction': 1})
            self.assertEqual(repaired['after_schedule']['missing_dates'], [])
            again = run(numbers, [source], '2021-01-06', root / 'again')
            self.assertEqual(again['changes'], [])
            self.assertEqual(again['changed_files'], [])
            self.assertTrue((root / 'repair' / 'before' / '2021.txt').exists())

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'NumPy needed for legacy loader')
    def test_legacy_loader_honors_path_and_has_no_shared_state(self):
        from selma.data import Numbers
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            Path(first, '2021.txt').write_text('2021-01-02\t6\t5\t4\t3\t2\t1\t0\n')
            Path(second, '2022.txt').write_text(HEADER + '\n2022-01-01\t7\t8\t9\t10\t11\t12\t1\n')
            a, b, c = Numbers(first), Numbers(second), Numbers(first)
            self.assertEqual(a.datum, ['2021-01-02'])
            self.assertEqual(b.datum, ['2022-01-01'])
            self.assertEqual(a.matrix.tolist(), [[1, 2, 3, 4, 5, 6, 0]])
            self.assertEqual(a.matrix.tolist(), c.matrix.tolist())
            a.parseNumbers()
            self.assertEqual(a.matrix.shape, (1, 7))


if __name__ == '__main__':
    unittest.main()
