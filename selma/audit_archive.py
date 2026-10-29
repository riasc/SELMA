"""Compare local draws to official WestLotto CSV ZIP downloads; optionally repair."""
import argparse
from collections import Counter
import csv
from datetime import date, datetime
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

from selma.archive import HEADER, load_records, schedule_gaps
from selma.config import NUMBERS_DIR, RESULTS_DIR


SOURCE_PAGE = 'https://www.lotto-thueringen.de/service/downloads/downloads.html'
CSV_ENDPOINT = 'https://www.westlotto.de/wlinfo/WL_InfoService'


def read_official(archives, through):
    records = {}
    sources = []
    excluded = Counter()
    for path in archives:
        path = Path(path)
        payload = path.read_bytes()
        members = []
        with ZipFile(io.BytesIO(payload)) as archive:
            for name in archive.namelist():
                if not name.endswith('.csv'):
                    raise ValueError(f'expected CSV ZIP member, got {name}')
                members.append(name)
                for line_no, cells in enumerate(csv.reader(archive.read(name).decode('cp1252').splitlines(), delimiter=';'), 1):
                    if not cells or not re.fullmatch(r'\d{2}\.\d{2}\.\d{4}', cells[0].strip()):
                        continue
                    day = datetime.strptime(cells[0].strip(), '%d.%m.%Y').date()
                    if day.isoformat() > through:
                        continue
                    # Preserve SELMA's main historical series. Older Wednesday
                    # 7/38 and Wednesday A/B 6/49 are distinct games, not gaps.
                    if day < date(2000, 12, 6) and day.weekday() == 2:
                        excluded['separate_pre_unification_Wednesday_games'] += 1
                        continue
                    if len(cells) < 11:
                        raise ValueError(f'{name}:{line_no}: truncated CSV row')
                    if cells[1].strip():
                        raise ValueError(f'{name}:{line_no}: unexpected draw type {cells[1]!r}')
                    numbers = tuple(sorted(map(int, cells[2:8])))
                    if len(set(numbers)) != 6 or not all(1 <= n <= 49 for n in numbers):
                        raise ValueError(f'{name}:{line_no}: invalid main numbers')
                    bonus = cells[10].strip()
                    sz = int(bonus) if bonus else -1
                    if not -1 <= sz <= 9:
                        raise ValueError(f'{name}:{line_no}: invalid Superzahl')
                    row = (day.isoformat(), numbers, sz)
                    if row[0] in records and records[row[0]] != row:
                        raise ValueError(f'conflicting official rows for {row[0]}')
                    records[row[0]] = row
        sources.append(dict(file=path.name, sha256=hashlib.sha256(payload).hexdigest(),
                            members=members, discovery_url=SOURCE_PAGE, endpoint=CSV_ENDPOINT))
    return sorted(records.values()), sources, dict(excluded)


def differences(local, official):
    old = {r[0]: r for r in local}
    new = {r[0]: r for r in official}
    missing = set(new) - set(old)
    changes = []
    for day in sorted(set(old) - set(new)):
        # Only permit date moves supported by identical numbers/SZ nearby.
        matches = [d for d in missing if old[day][1:] == new[d][1:]
                   and abs((date.fromisoformat(day) - date.fromisoformat(d)).days) <= 7]
        if len(matches) != 1:
            raise ValueError(f'local-only draw {day} cannot be safely reconciled; inspect sources')
        target = matches[0]
        missing.remove(target)
        changes.append(dict(kind='date_correction', old=old[day], new=new[target]))
    changes.extend(dict(kind='missing_draw', old=None, new=new[d]) for d in sorted(missing))
    for day in sorted(set(old) & set(new)):
        if old[day] != new[day]:
            changes.append(dict(kind='result_correction', old=old[day], new=new[day]))
    return changes


def auto_mergeable(changes, format_changes, last_local, today, limit=10):
    """True only for a small batch of brand-new draws dated after the last local draw."""
    return (not format_changes and 1 <= len(changes) <= limit
            and all(c['kind'] == 'missing_draw' and last_local < c['new'][0] <= today for c in changes))


def run(directory, archives, through, output, apply=False):
    directory, output = Path(directory), Path(output)
    local = load_records(directory)
    if not local:
        raise ValueError('local archive is empty')
    if any(r[0] > through for r in local):
        raise ValueError('through must include every local draw; refusing to truncate data')
    official, sources, excluded = read_official(archives, through)
    if not official or official[0][0] > local[0][0]:
        raise ValueError('official sources do not cover the beginning of the local archive')
    gaps = schedule_gaps(official, through)
    if any(gaps.values()):
        raise ValueError(f'official reference has schedule discrepancies: {gaps}')
    changes = differences(local, official)
    format_changes = []
    by_year = {}
    for day, numbers, sz in official:
        by_year.setdefault(day[:4], []).append('\t'.join(map(str, (day, *numbers, sz))))
    prepared = {}
    for year, lines in by_year.items():
        path = directory / f'{year}.txt'
        content = HEADER + '\n' + '\n'.join(lines) + '\n'
        old_content = path.read_text() if path.exists() else ''
        if old_content.rstrip('\n') != content.rstrip('\n'):
            prepared[path] = content
        if old_content and old_content.splitlines()[0] != HEADER:
            format_changes.append(dict(file=path.name, issue='missing_header'))
    report = dict(through=through, before_count=len(local), official_count=len(official),
                  applied=apply, sources=sources, excluded=excluded,
                  change_counts=dict(Counter(c['kind'] for c in changes)), changes=changes,
                  format_changes=format_changes,
                  auto_mergeable=auto_mergeable(changes, format_changes, local[-1][0], date.today().isoformat()),
                  before_schedule=schedule_gaps(local, through),
                  official_schedule=gaps, changed_files=[p.name for p in prepared],
                  notes=[
                      'Scope: original weekend series through 2000-12-02, unified Wed/Sat series from 2000-12-06; earlier Sunday dates retained as supplied by the official CSV.',
                      'Official CSV columns 2:8 contain the six main numbers; column 10 is Superzahl, not Zusatzzahl. Blank Superzahl maps to -1.',
                      'Current official CSV is the canonical reference. The older 2021 Excel ZIP disagrees on dates for two 1966 holiday draws and two July 2014/2015 draws; CSV dates take precedence.',
                      'Original files and previous evaluation summaries were preserved in results/archive_audit before repair.',
                  ])
    output.mkdir(parents=True, exist_ok=True)
    if apply:
        backup = output / 'before'
        backup.mkdir(exist_ok=True)
        for path, content in prepared.items():
            if path.exists():
                target = backup / path.name
                if target.exists():
                    raise ValueError(f'backup exists: {target}; use a new output directory')
        for path, content in prepared.items():
            if path.exists():
                (backup / path.name).write_bytes(path.read_bytes())
            path.write_text(content)
        repaired = load_records(directory)
        if repaired != official:
            raise ValueError('post-repair verification differs from official records')
        report['after_count'] = len(repaired)
        report['after_schedule'] = schedule_gaps(repaired, through)
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-zip', type=Path, action='append', required=True)
    parser.add_argument('--through', type=lambda x: date.fromisoformat(x).isoformat(), required=True)
    parser.add_argument('--numbers', type=Path, default=Path(NUMBERS_DIR))
    parser.add_argument('--output', type=Path, default=Path(RESULTS_DIR) / 'archive_audit' / 'comparison')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        report = run(args.numbers, args.official_zip, args.through, args.output, args.apply)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({k: report[k] for k in ('before_count', 'official_count', 'applied', 'change_counts', 'format_changes', 'changed_files')}, indent=2))
    print(f'Report: {args.output / "report.json"}')


if __name__ == '__main__':
    main()
