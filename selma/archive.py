"""Validated access to SELMA's dated main-number and Superzahl records."""
from datetime import date, timedelta
from pathlib import Path

HEADER = 'Date\t1\t2\t3\t4\t5\t6\tSZ'


def load_records(directory):
    """Read headered or headerless year files without dropping the first draw."""
    records = []
    seen = set()
    for path in sorted(Path(directory).glob('*.txt')):
        with path.open(encoding='utf-8-sig') as source:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                cells = line.strip().split('\t')
                if cells[0] == 'Date':
                    if line_number != 1 or line.strip() != HEADER:
                        raise ValueError(f'{path}:{line_number}: unexpected header')
                    continue
                try:
                    if len(cells) != 8:
                        raise ValueError('expected date, six main numbers and Superzahl')
                    day = date.fromisoformat(cells[0]).isoformat()
                    if day != cells[0]:
                        raise ValueError('date must use YYYY-MM-DD')
                    if path.stem.isdigit() and int(path.stem) != int(day[:4]):
                        raise ValueError('draw year differs from filename')
                    numbers = tuple(sorted(map(int, cells[1:7])))
                    if len(set(numbers)) != 6:
                        raise ValueError('expected six distinct numbers')
                    if not all(1 <= n <= 49 for n in numbers):
                        raise ValueError('number outside 1–49')
                    superzahl = int(cells[7])
                    if not -1 <= superzahl <= 9:
                        raise ValueError('Superzahl outside -1 or 0–9')
                    if day in seen:
                        raise ValueError('duplicate date')
                except (ValueError, IndexError) as error:
                    raise ValueError(f'{path}:{line_number}: {error}') from error
                seen.add(day)
                records.append((day, numbers, superzahl))
    return sorted(records)


def schedule_gaps(records, through=None):
    """Check the unified Wed/Sat series from 2000-12-06, not earlier games."""
    if not records:
        return {'missing_dates': [], 'unexpected_dates': []}
    dates = {date.fromisoformat(row[0]) for row in records}
    start = max(min(dates), date(2000, 12, 6))
    end = date.fromisoformat(through) if through else max(dates)
    expected = set()
    day = start
    while day <= end:
        if day.weekday() in (2, 5):
            expected.add(day)
        day += timedelta(days=1)
    return dict(missing_dates=sorted(d.isoformat() for d in expected - dates),
                unexpected_dates=sorted(d.isoformat() for d in dates if start <= d <= end and d not in expected))
