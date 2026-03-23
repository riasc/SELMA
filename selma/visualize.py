import os
import json

from selma.config import BASE_DIR, COLLECT_DIR
from selma.profiles import Profiles
from selma.oddeven import OddEven, ODDEVEN_DIR
from selma.templates import Templates, TEMPLATES_DIR
from selma.sumrange import SumRange, SUMRANGE_DIR
from selma.distance import DrawDistance, DISTANCE_DIR
from selma.consecutive import Consecutive, CONSECUTIVE_DIR
from selma.hotcold import HotCold, HOTCOLD_DIR

DOCS_DIR = os.path.join(BASE_DIR, "docs")


def load_profile_data():
    """Load cumulative profiles and return as JSON-serializable dict."""
    profiles = Profiles.load()

    data = {}
    for num in range(1, 50):
        data[num] = {}
        if num in profiles.cumulative:
            for year in profiles.years:
                if year in profiles.cumulative[num]:
                    data[num][year] = profiles.cumulative[num][year]

    return data, profiles.years, profiles.year_draw_counts


def load_oddeven_data():
    """Load odd/even occurrence and frequency data."""
    # load frequency
    freq = {}
    with open(os.path.join(ODDEVEN_DIR, "frequency.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("odd"):
                continue
            cells = line.split("\t")
            key = cells[0] + "/" + cells[1]
            freq[key] = {"count": int(cells[2]), "probability": float(cells[3])}

    # load occurrence
    occ = []
    with open(os.path.join(ODDEVEN_DIR, "occurrence.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("date"):
                continue
            cells = line.split("\t")
            occ.append({"date": cells[0], "odd": int(cells[1]), "even": int(cells[2])})

    return freq, occ


def load_templates_data():
    """Load templates occurrence data."""
    occ = []
    with open(os.path.join(TEMPLATES_DIR, "occurrence.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("date"):
                continue
            cells = line.split("\t")
            groups = [int(c) for c in cells[3:9]]
            spread = len(set(groups))
            occ.append({
                "date": cells[0],
                "groups": groups,
                "spread": spread,
            })
    return occ


def load_sumrange_data():
    """Load sum range occurrence data."""
    occ = []
    with open(os.path.join(SUMRANGE_DIR, "occurrence.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("date"):
                continue
            cells = line.split("\t")
            occ.append({"date": cells[0], "sum": int(cells[1])})
    return occ


def load_distance_data():
    """Load distance frequency and per-draw recency scores from collect/."""
    freq = []
    with open(os.path.join(DISTANCE_DIR, "frequency.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("recency"):
                continue
            cells = line.split("\t")
            freq.append({"score": int(cells[0]), "count": int(cells[1]), "probability": float(cells[2])})
    freq.sort(key=lambda x: x["score"])

    draw_scores = []
    with open(os.path.join(DISTANCE_DIR, "scores.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("date"):
                continue
            cells = line.split("\t")
            score = int(cells[1]) if len(cells) > 1 and cells[1] else None
            draw_scores.append({"date": cells[0], "score": score})

    return freq, draw_scores


def load_consecutive_data():
    """Load consecutive pairs occurrence data."""
    occ = []
    with open(os.path.join(CONSECUTIVE_DIR, "occurrence.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("date"):
                continue
            cells = line.split("\t")
            pairs_str = cells[2] if len(cells) > 2 else ""
            consec_pairs = pairs_str.split(",") if pairs_str else []
            occ.append({
                "date": cells[0],
                "pairs": int(cells[1]),
                "consec_pairs": consec_pairs,
            })
    return occ


def load_hotcold_data():
    """Load hot/cold frequency data."""
    freq = {}
    with open(os.path.join(HOTCOLD_DIR, "frequency.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("number"):
                continue
            cells = line.split("\t")
            num = int(cells[0])
            freq[num] = {
                "total": int(cells[1]),
                "rate_all": float(cells[2]),
                "rate_20": float(cells[3]),
                "rate_50": float(cells[4]),
                "rate_100": float(cells[5]),
                "trend": cells[6],
            }
    return freq


def load_yearly_data():
    """Load per-number, per-year frequency data for heatmap."""
    years = []
    data = {}  # data[number] = {year: count}
    with open(os.path.join(HOTCOLD_DIR, "frequency_yearly.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cells = line.split("\t")
            if cells[0] == "number":
                years = cells[1:]
                continue
            num = int(cells[0])
            data[num] = {}
            for i, year in enumerate(years):
                data[num][year] = int(cells[i + 1])
    return data, years


def load_gap_data():
    """Compute current gap (draws since last appearance) for each number."""
    from selma.distance import DISTANCE_DIR
    occurrence = {}
    total_draws = 0

    with open(os.path.join(DISTANCE_DIR, "meta.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("key"):
                continue
            cells = line.split("\t")
            if cells[0] == "total_draws":
                total_draws = int(cells[1])

    with open(os.path.join(DISTANCE_DIR, "occurrence.tsv"), "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("number"):
                continue
            cells = line.split("\t")
            num = int(cells[0])
            indices = [int(c) for c in cells[1:]]
            occurrence[num] = indices

    gaps = {}
    for num in range(1, 50):
        if num in occurrence and occurrence[num]:
            gaps[num] = {
                "current_gap": total_draws - occurrence[num][-1],
                "avg_gap": sum(occurrence[num][i] - occurrence[num][i-1] for i in range(1, len(occurrence[num]))) / max(1, len(occurrence[num]) - 1),
                "max_gap": max(occurrence[num][i] - occurrence[num][i-1] for i in range(1, len(occurrence[num]))) if len(occurrence[num]) > 1 else 0,
                "total_appearances": len(occurrence[num]),
            }
        else:
            gaps[num] = {"current_gap": total_draws, "avg_gap": 0, "max_gap": 0, "total_appearances": 0}

    return gaps, total_draws


def load_draws_data():
    """Load all draws directly from numbers/*.txt files."""
    import datetime as dt
    from selma.config import NUMBERS_DIR

    draws = []
    for filename in sorted(os.listdir(NUMBERS_DIR)):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(NUMBERS_DIR, filename)
        with open(filepath, "r") as f:
            next(f)  # skip header
            for line in f:
                line = line.strip()
                if not line:
                    continue
                cells = line.split("\t")
                if len(cells) < 8:
                    continue
                date = cells[0].strip()
                numbers = sorted([int(cells[i]) for i in range(1, 7)])
                sz = int(cells[7])
                d = dt.datetime.strptime(date, "%Y-%m-%d")
                day = "Mi" if d.weekday() == 2 else "Sa"
                draws.append({
                    "date": date,
                    "day": day,
                    "numbers": numbers,
                    "sz": sz,
                })
    return draws


# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------

SHARED_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; display: flex; height: 100vh; background: #f5f5f5; }

/* Sidebar */
.sidebar {
    width: 260px;
    background: #1a1a2e;
    color: #e0e0e0;
    padding: 20px;
    overflow-y: auto;
    flex-shrink: 0;
}
.sidebar h1 { font-size: 20px; color: #fff; margin-bottom: 20px; }
.sidebar h2 {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #888;
    margin: 20px 0 10px;
}
.sidebar .section { margin-bottom: 15px; }
.sidebar .section-item {
    display: block;
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 2px;
    font-size: 14px;
    color: #e0e0e0;
    text-decoration: none;
}
.sidebar .section-item:hover { background: #16213e; }
.sidebar .section-item.active { background: #0f3460; color: #fff; }

/* Main content */
.main { flex: 1; padding: 30px; overflow-y: auto; }
.main h2 { font-size: 22px; margin-bottom: 20px; color: #1a1a2e; }

/* Controls */
.controls { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
.controls label { font-size: 14px; color: #555; }
.controls select, .controls input {
    padding: 6px 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 14px;
}

/* Number grid */
.number-grid {
    display: grid;
    grid-template-columns: repeat(10, 1fr);
    gap: 4px;
    margin-bottom: 20px;
    max-width: 500px;
}
.number-btn {
    padding: 8px 4px;
    text-align: center;
    border: 1px solid #ccc;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    background: #fff;
    user-select: none;
}
.number-btn:hover { background: #e8e8e8; }
.number-btn.selected { background: #0f3460; color: #fff; border-color: #0f3460; }

/* Chart */
.chart-container {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    position: relative;
    height: 500px;
    margin-bottom: 20px;
}

/* Draw history */
.draw-row {
    display: flex;
    align-items: center;
    padding: 6px 12px;
    border-bottom: 1px solid #eee;
    font-size: 14px;
}
.draw-row:hover { background: #f0f4ff; }
.draw-date { width: 110px; font-weight: 500; color: #333; }
.draw-day { width: 35px; color: #888; font-size: 12px; }
.draw-balls { display: flex; gap: 6px; }
.draw-ball {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 14px;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
.draw-ball.g0 { background: #e6194b; }
.draw-ball.g1 { background: #3cb44b; }
.draw-ball.g2 { background: #4363d8; }
.draw-ball.g3 { background: #f58231; }
.draw-ball.g4 { background: #911eb4; }
.draw-ball.odd { background: #4363d8; }
.draw-ball.even { background: #e6194b; }
.draw-ball.highlight {
    box-shadow: 0 0 0 3px #000, 0 0 0 5px #ffd700;
}
.draw-sz {
    margin-left: 12px;
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 600; font-size: 12px;
    background: #ddd; color: #333;
    border: 2px solid #bbb;
}
.draw-header {
    display: flex; align-items: center; padding: 8px 12px;
    font-size: 12px; color: #888; border-bottom: 2px solid #ccc;
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
}
"""


# ---------------------------------------------------------------------------
# Sidebar JS (shared across pages)
# ---------------------------------------------------------------------------

SIDEBAR_JS = """\
(function() {
    const pages = [
        { id: 'drawhistory', label: 'Draw History', href: 'index.html', section: 'draws' },
        { id: 'profiles', label: 'Profiles', href: 'profiles.html', section: 'analysis' },
        { id: 'oddeven', label: 'Odd / Even', href: 'oddeven.html', section: 'analysis' },
        { id: 'numgroups', label: 'Number Groups', href: 'numgroups.html', section: 'analysis' },
        { id: 'sumrange', label: 'Sum Range', href: 'sumrange.html', section: 'analysis' },
        { id: 'distance', label: 'Recency', href: 'distance.html', section: 'analysis' },
        { id: 'consecutive', label: 'Consecutive', href: 'consecutive.html', section: 'analysis' },
        { id: 'hotcold', label: 'Hot / Cold', href: 'hotcold.html', section: 'analysis' },
        { id: 'gaps', label: 'Gaps', href: 'gaps.html', section: 'analysis' },
    ];

    const currentPage = document.body.getAttribute('data-page');
    const sidebar = document.getElementById('sidebar');

    let html = '<h1>SELMA</h1>';
    html += '<h2>Draws</h2><div class="section">';
    pages.filter(p => p.section === 'draws').forEach(p => {
        const cls = p.id === currentPage ? ' active' : '';
        html += '<a class="section-item' + cls + '" href="' + p.href + '">' + p.label + '</a>';
    });
    html += '</div>';
    html += '<h2>Analysis</h2><div class="section">';
    pages.filter(p => p.section === 'analysis').forEach(p => {
        const cls = p.id === currentPage ? ' active' : '';
        html += '<a class="section-item' + cls + '" href="' + p.href + '">' + p.label + '</a>';
    });
    html += '</div>';

    sidebar.innerHTML = html;
})();
"""


# ---------------------------------------------------------------------------
# Shared colors (used across page scripts)
# ---------------------------------------------------------------------------

COLORS_JS = """\
const colors = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
    '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990'
];
const colorsDimmed = [
    '#e6194b66', '#3cb44b66', '#4363d866', '#f5823166', '#911eb466',
    '#42d4f466', '#f032e666', '#bfef4566', '#fabed466', '#46999066'
];
"""


# ---------------------------------------------------------------------------
# Page-specific HTML content and JS
# ---------------------------------------------------------------------------

def _page_drawhistory_content():
    return """\
            <h2>Draw History</h2>

            <div class="controls">
                <label>Year:</label>
                <select id="draws-year"></select>
                <label style="margin-left: 10px;">Highlight number:</label>
                <input type="number" id="draws-highlight" min="1" max="49" placeholder="1-49" style="width: 70px;">
                <label style="margin-left: 10px;">Day:</label>
                <select id="draws-day">
                    <option value="">All</option>
                    <option value="Mi">Mi (Wed)</option>
                    <option value="Sa">Sa (Sat)</option>
                </select>
                <label style="margin-left: 10px;">Color:</label>
                <select id="draws-color">
                    <option value="group" selected>Decade group</option>
                    <option value="oddeven">Odd / Even</option>
                </select>
            </div>

            <div id="draws-container" style="margin-top: 15px;"></div>
"""


def _page_drawhistory_js():
    return """\
    // build date->recency lookup from distanceScores
    const recencyByDate = {};
    distanceScores.forEach(d => {
        if (d.score !== null) recencyByDate[d.date] = d.score;
    });

    const yearSelect = document.getElementById('draws-year');
    const drawYears = [...new Set(drawsData.map(d => d.date.split('-')[0]))].sort().reverse();
    drawYears.forEach(y => yearSelect.add(new Option(y, y)));
    yearSelect.value = drawYears[0];

    yearSelect.addEventListener('change', renderDraws);
    document.getElementById('draws-highlight').addEventListener('input', renderDraws);
    document.getElementById('draws-day').addEventListener('change', renderDraws);
    document.getElementById('draws-color').addEventListener('change', renderDraws);

    function getDecadeClass(n) {
        if (n <= 9) return 'g0';
        if (n <= 19) return 'g1';
        if (n <= 29) return 'g2';
        if (n <= 39) return 'g3';
        return 'g4';
    }

    function getBallClass(n, colorMode) {
        if (colorMode === 'oddeven') {
            return n % 2 === 1 ? 'odd' : 'even';
        }
        return getDecadeClass(n);
    }

    function renderDraws() {
        const year = document.getElementById('draws-year').value;
        const highlightNum = parseInt(document.getElementById('draws-highlight').value) || 0;
        const dayFilter = document.getElementById('draws-day').value;
        const colorMode = document.getElementById('draws-color').value;

        let filtered = drawsData.filter(d => d.date.startsWith(year));
        if (dayFilter) {
            filtered = filtered.filter(d => d.day === dayFilter);
        }
        // show newest first
        filtered = filtered.slice().reverse();

        const container = document.getElementById('draws-container');
        let html = '';

        // legend
        html += '<div style="padding: 8px 12px; font-size: 11px; color: #888; border-bottom: 1px solid #eee;">';
        if (colorMode === 'group') {
            html += '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#e6194b;margin-right:2px;vertical-align:middle;"></span> 1-9 ';
            html += '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#3cb44b;margin-right:2px;vertical-align:middle;margin-left:8px;"></span> 10-19 ';
            html += '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#4363d8;margin-right:2px;vertical-align:middle;margin-left:8px;"></span> 20-29 ';
            html += '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f58231;margin-right:2px;vertical-align:middle;margin-left:8px;"></span> 30-39 ';
            html += '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#911eb4;margin-right:2px;vertical-align:middle;margin-left:8px;"></span> 40-49';
        } else {
            html += '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#4363d8;margin-right:2px;vertical-align:middle;"></span> Odd ';
            html += '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#e6194b;margin-right:2px;vertical-align:middle;margin-left:8px;"></span> Even';
        }
        html += '<span style="margin-left: 20px;">| Sum = sum of 6 numbers | Rec = recency score (sum of gaps since each number last appeared)</span>';
        html += '</div>';

        // header
        html += '<div class="draw-header">';
        html += '<span class="draw-date">Date</span>';
        html += '<span class="draw-day">Day</span>';
        html += '<div class="draw-balls" style="pointer-events:none;">';
        for (let i = 1; i <= 6; i++) {
            html += '<div style="width:36px;text-align:center;font-size:11px;">Z' + i + '</div>';
        }
        html += '</div>';
        html += '<div style="width:28px;text-align:center;font-size:11px;margin-left:12px;">SZ</div>';
        html += '<span style="margin-left:12px;min-width:35px;text-align:right;font-size:11px;">Sum</span>';
        html += '<span style="margin-left:12px;min-width:35px;text-align:right;font-size:11px;">Rec</span>';
        html += '</div>';

        filtered.forEach(draw => {
            html += '<div class="draw-row">';
            html += '<span class="draw-date">' + draw.date + '</span>';
            html += '<span class="draw-day">' + draw.day + '</span>';
            html += '<div class="draw-balls">';
            draw.numbers.forEach(n => {
                const hl = (highlightNum > 0 && n === highlightNum) ? ' highlight' : '';
                html += '<div class="draw-ball ' + getBallClass(n, colorMode) + hl + '">' + n + '</div>';
            });
            html += '</div>';
            const szVal = draw.sz >= 0 ? draw.sz : '-';
            html += '<div class="draw-sz">' + szVal + '</div>';
            const comboSum = draw.numbers.reduce((a, b) => a + b, 0);
            html += '<span style="margin-left: 12px; font-size: 13px; color: #888; min-width: 35px; text-align: right;">' + comboSum + '</span>';
            const rec = recencyByDate[draw.date];
            html += '<span style="margin-left: 12px; font-size: 13px; color: #888; min-width: 35px; text-align: right;">' + (rec !== undefined ? rec : '-') + '</span>';
            html += '</div>';
        });

        if (filtered.length === 0) {
            html += '<div style="padding: 20px; color: #888;">No draws found</div>';
        }

        container.innerHTML = html;
    }

    renderDraws();
"""


def _page_profiles_content():
    return """\
            <h2>Yearly Trajectory Profiles</h2>

            <div class="controls">
                <label>Year:</label>
                <select id="year-select"></select>
                <label style="margin-left: 10px;">Compare with:</label>
                <select id="compare-year-select">
                    <option value="">-- none --</option>
                </select>
            </div>

            <p style="font-size: 13px; color: #888; margin-bottom: 10px;">
                Select numbers to plot their cumulative draw count over the year.
            </p>

            <div class="number-grid" id="number-grid"></div>

            <div class="chart-container">
                <canvas id="profile-chart"></canvas>
            </div>
"""


def _page_profiles_js():
    return COLORS_JS + """\
    let selectedNumbers = [];
    let profileChart = null;

    const yearSelect = document.getElementById('year-select');
    const compareSelect = document.getElementById('compare-year-select');
    years.forEach(y => {
        yearSelect.add(new Option(y, y));
        compareSelect.add(new Option(y, y));
    });
    yearSelect.value = years[years.length - 1];

    const grid = document.getElementById('number-grid');
    for (let n = 1; n <= 49; n++) {
        const btn = document.createElement('div');
        btn.className = 'number-btn';
        btn.textContent = n;
        btn.dataset.num = n;
        btn.addEventListener('click', () => {
            const idx = selectedNumbers.indexOf(n);
            if (idx >= 0) {
                selectedNumbers.splice(idx, 1);
                btn.classList.remove('selected');
            } else {
                if (selectedNumbers.length >= 10) return;
                selectedNumbers.push(n);
                btn.classList.add('selected');
            }
            updateProfileChart();
        });
        grid.appendChild(btn);
    }

    function updateProfileChart() {
        const year = yearSelect.value;
        const compareYear = compareSelect.value;
        const maxDraws = Math.max(
            yearDrawCounts[year] || 0,
            compareYear ? (yearDrawCounts[compareYear] || 0) : 0
        );
        const labels = Array.from({length: maxDraws}, (_, i) => i + 1);
        const datasets = [];

        selectedNumbers.forEach((num, i) => {
            const color = colors[i % colors.length];
            const dimmed = colorsDimmed[i % colorsDimmed.length];
            if (profileData[num] && profileData[num][year]) {
                datasets.push({
                    label: 'Nr ' + num + ' (' + year + ')',
                    data: profileData[num][year],
                    borderColor: color, backgroundColor: 'transparent',
                    borderWidth: 2, pointRadius: 0, tension: 0.1,
                });
            }
            if (compareYear && profileData[num] && profileData[num][compareYear]) {
                datasets.push({
                    label: 'Nr ' + num + ' (' + compareYear + ')',
                    data: profileData[num][compareYear],
                    borderColor: dimmed, backgroundColor: 'transparent',
                    borderWidth: 2, borderDash: [5, 5], pointRadius: 0, tension: 0.1,
                });
            }
        });

        if (profileChart) profileChart.destroy();
        profileChart = new Chart(document.getElementById('profile-chart'), {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { font: { size: 12 } } },
                    tooltip: { mode: 'index', intersect: false },
                },
                scales: {
                    x: { title: { display: true, text: 'Draw in year' }, ticks: { maxTicksLimit: 20 } },
                    y: { title: { display: true, text: 'Cumulative count' }, beginAtZero: true },
                }
            }
        });
    }

    yearSelect.addEventListener('change', updateProfileChart);
    compareSelect.addEventListener('change', updateProfileChart);
    updateProfileChart();
"""


def _page_oddeven_content():
    return """\
            <h2>Odd / Even Ratio</h2>

            <div class="controls">
                <label>From:</label>
                <select id="oddeven-from-year"></select>
                <label>To:</label>
                <select id="oddeven-to-year"></select>
            </div>

            <div class="chart-container">
                <canvas id="oddeven-freq-chart"></canvas>
            </div>

            <div class="controls">
                <label>Timeline - show last:</label>
                <select id="oddeven-range">
                    <option value="50">50 draws</option>
                    <option value="100">100 draws</option>
                    <option value="200">200 draws</option>
                    <option value="500">500 draws</option>
                    <option value="0" selected>All draws</option>
                </select>
            </div>

            <div class="chart-container" style="height: 350px;">
                <canvas id="oddeven-timeline-chart"></canvas>
            </div>
"""


def _page_oddeven_js():
    return """\
    let oddevenFreqChart = null;
    let oddevenTimelineChart = null;

    // populate year range selects
    const fromSelect = document.getElementById('oddeven-from-year');
    const toSelect = document.getElementById('oddeven-to-year');
    const oeYears = [...new Set(oddevenOcc.map(d => d.date.split('-')[0]))].sort();
    oeYears.forEach(y => {
        fromSelect.add(new Option(y, y));
        toSelect.add(new Option(y, y));
    });
    fromSelect.value = oeYears[0];
    toSelect.value = oeYears[oeYears.length - 1];

    fromSelect.addEventListener('change', updateOddEvenFreqChart);
    toSelect.addEventListener('change', updateOddEvenFreqChart);
    document.getElementById('oddeven-range').addEventListener('change', updateOddEvenTimeline);

    function updateOddEvenFreqChart() {
        const fromYear = document.getElementById('oddeven-from-year').value;
        const toYear = document.getElementById('oddeven-to-year').value;

        // filter occurrence data by year range
        const filtered = oddevenOcc.filter(d => {
            const y = d.date.split('-')[0];
            return y >= fromYear && y <= toYear;
        });

        // count ratios from filtered data
        const ratioCount = {};
        filtered.forEach(d => {
            const key = d.odd + '/' + d.even;
            ratioCount[key] = (ratioCount[key] || 0) + 1;
        });

        const keys = Object.keys(ratioCount).sort((a, b) => {
            const [ao] = a.split('/').map(Number);
            const [bo] = b.split('/').map(Number);
            return bo - ao;
        });
        const labels = keys.map(k => k.replace('/', ' odd / ') + ' even');
        const counts = keys.map(k => ratioCount[k]);
        const total = counts.reduce((a, b) => a + b, 0);
        const pcts = counts.map(c => ((c / total) * 100).toFixed(1));

        const barColors = keys.map(k => {
            const odd = parseInt(k.split('/')[0]);
            if (odd === 3) return '#3cb44b';
            if (odd === 2 || odd === 4) return '#4363d8';
            return '#e6194b';
        });

        const titleText = 'Distribution of Odd/Even Ratios (' + fromYear + ' - ' + toYear + ', ' + total + ' draws)';

        if (oddevenFreqChart) oddevenFreqChart.destroy();
        oddevenFreqChart = new Chart(document.getElementById('oddeven-freq-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: barColors,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Count: ' + ctx.raw + ' (' + pcts[ctx.dataIndex] + '%)'
                        }
                    },
                    title: { display: true, text: titleText, font: { size: 16 } },
                },
                scales: {
                    x: { title: { display: true, text: 'Ratio' } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                }
            }
        });
    }

    function updateOddEvenTimeline() {
        const range = parseInt(document.getElementById('oddeven-range').value);
        let data = oddevenOcc;
        if (range > 0) {
            data = data.slice(-range);
        }

        const labels = data.map(d => d.date);
        const oddCounts = data.map(d => d.odd);

        // compute rolling average (window of 20)
        const window = 20;
        const rolling = oddCounts.map((_, i) => {
            const start = Math.max(0, i - window + 1);
            const slice = oddCounts.slice(start, i + 1);
            return slice.reduce((a, b) => a + b, 0) / slice.length;
        });

        if (oddevenTimelineChart) oddevenTimelineChart.destroy();
        oddevenTimelineChart = new Chart(document.getElementById('oddeven-timeline-chart'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Odd count per draw',
                        data: oddCounts,
                        borderColor: '#4363d844',
                        backgroundColor: '#4363d822',
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: true,
                    },
                    {
                        label: 'Rolling avg (20 draws)',
                        data: rolling,
                        borderColor: '#e6194b',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 0,
                    },
                    {
                        label: 'Expected (3)',
                        data: Array(data.length).fill(3),
                        borderColor: '#88888866',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { font: { size: 12 } } },
                    title: { display: true, text: 'Odd Numbers per Draw Over Time', font: { size: 16 } },
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Draw date' },
                        ticks: { maxTicksLimit: 15, maxRotation: 45 },
                    },
                    y: {
                        title: { display: true, text: 'Odd count' },
                        min: 0, max: 6,
                    }
                }
            }
        });
    }

    updateOddEvenFreqChart();
    updateOddEvenTimeline();
"""


def _page_numgroups_content():
    return """\
            <h2>Number Groups</h2>
            <p style="font-size: 13px; color: #888; margin-bottom: 15px;">
                Numbers grouped into decades: 0 = 1-9, 1 = 10-19, 2 = 20-29, 3 = 30-39, 4 = 40-49
            </p>

            <div class="controls">
                <label>From:</label>
                <select id="numgroups-from-year"></select>
                <label>To:</label>
                <select id="numgroups-to-year"></select>
            </div>

            <div class="chart-container">
                <canvas id="numgroups-decade-chart"></canvas>
            </div>

            <div class="chart-container">
                <canvas id="numgroups-spread-chart"></canvas>
            </div>

            <div class="chart-container" style="height: 600px;">
                <canvas id="numgroups-patterns-chart"></canvas>
            </div>

            <div class="controls">
                <label>Timeline - show last:</label>
                <select id="numgroups-range">
                    <option value="50">50 draws</option>
                    <option value="100">100 draws</option>
                    <option value="200">200 draws</option>
                    <option value="500">500 draws</option>
                    <option value="0" selected>All draws</option>
                </select>
            </div>

            <div class="chart-container" style="height: 350px;">
                <canvas id="numgroups-timeline-chart"></canvas>
            </div>
"""


def _page_numgroups_js():
    return """\
    let numgroupsDecadeChart = null;
    let numgroupsSpreadChart = null;
    let numgroupsTimelineChart = null;
    let numgroupsPatternsChart = null;

    const decadeLabels = ['1-9', '10-19', '20-29', '30-39', '40-49'];
    const decadeColors = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4'];

    const fromSelect = document.getElementById('numgroups-from-year');
    const toSelect = document.getElementById('numgroups-to-year');
    const ngYears = [...new Set(templatesOcc.map(d => d.date.split('-')[0]))].sort();
    ngYears.forEach(y => {
        fromSelect.add(new Option(y, y));
        toSelect.add(new Option(y, y));
    });
    fromSelect.value = ngYears[0];
    toSelect.value = ngYears[ngYears.length - 1];

    fromSelect.addEventListener('change', updateNumGroupsCharts);
    toSelect.addEventListener('change', updateNumGroupsCharts);
    document.getElementById('numgroups-range').addEventListener('change', updateNumGroupsTimeline);

    function updateNumGroupsCharts() {
        const fromYear = document.getElementById('numgroups-from-year').value;
        const toYear = document.getElementById('numgroups-to-year').value;

        const filtered = templatesOcc.filter(d => {
            const y = d.date.split('-')[0];
            return y >= fromYear && y <= toYear;
        });

        const total = filtered.length;

        // decade frequency: how often each group appears across all draws
        const decadeCounts = [0, 0, 0, 0, 0];
        filtered.forEach(d => {
            d.groups.forEach(g => { decadeCounts[g]++; });
        });

        const titleDecade = 'Numbers per Decade Group (' + fromYear + ' - ' + toYear + ', ' + total + ' draws)';

        if (numgroupsDecadeChart) numgroupsDecadeChart.destroy();
        numgroupsDecadeChart = new Chart(document.getElementById('numgroups-decade-chart'), {
            type: 'bar',
            data: {
                labels: decadeLabels,
                datasets: [{
                    label: 'Count',
                    data: decadeCounts,
                    backgroundColor: decadeColors,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const pct = ((ctx.raw / (total * 6)) * 100).toFixed(1);
                                return 'Count: ' + ctx.raw + ' (' + pct + '% of all drawn numbers)';
                            }
                        }
                    },
                    title: { display: true, text: titleDecade, font: { size: 16 } },
                },
                scales: {
                    x: { title: { display: true, text: 'Decade group' } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                }
            }
        });

        // spread distribution
        const spreadCounts = {};
        filtered.forEach(d => {
            const s = d.spread;
            spreadCounts[s] = (spreadCounts[s] || 0) + 1;
        });

        const spreadKeys = Object.keys(spreadCounts).map(Number).sort();
        const spreadLabels = spreadKeys.map(k => k + ' of 5');
        const spreadData = spreadKeys.map(k => spreadCounts[k]);
        const spreadPcts = spreadData.map(c => ((c / total) * 100).toFixed(1));

        const spreadBarColors = spreadKeys.map(k => {
            if (k >= 4) return '#3cb44b';
            if (k === 3) return '#4363d8';
            return '#e6194b';
        });

        const titleSpread = 'Decade Spread: How many of the 5 groups are represented per draw (' + fromYear + ' - ' + toYear + ')';

        if (numgroupsSpreadChart) numgroupsSpreadChart.destroy();
        numgroupsSpreadChart = new Chart(document.getElementById('numgroups-spread-chart'), {
            type: 'bar',
            data: {
                labels: spreadLabels,
                datasets: [{
                    label: 'Count',
                    data: spreadData,
                    backgroundColor: spreadBarColors,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Count: ' + ctx.raw + ' (' + spreadPcts[ctx.dataIndex] + '%)'
                        }
                    },
                    title: { display: true, text: titleSpread, font: { size: 16 } },
                },
                scales: {
                    x: { title: { display: true, text: 'Decades covered' } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                }
            }
        });

        // top N most common group patterns
        updateNumGroupsPatterns(filtered, fromYear, toYear);
    }

    function updateNumGroupsPatterns(filtered, fromYear, toYear) {
        const patternCounts = {};
        filtered.forEach(d => {
            const key = d.groups.join('-');
            patternCounts[key] = (patternCounts[key] || 0) + 1;
        });

        const sorted = Object.entries(patternCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 20);

        const total = filtered.length;
        const labels = sorted.map(([k, _]) => {
            const groups = k.split('-').map(Number);
            return groups.map(g => decadeLabels[g]).join(', ');
        });
        const counts = sorted.map(([_, c]) => c);
        const pcts = counts.map(c => ((c / total) * 100).toFixed(1));

        // color by spread
        const barColors = sorted.map(([k, _]) => {
            const spread = new Set(k.split('-')).size;
            if (spread === 5) return '#3cb44b';
            if (spread === 4) return '#4363d8';
            if (spread === 3) return '#f58231';
            return '#e6194b';
        });

        const titlePatterns = 'Top 20 Group Patterns (' + fromYear + ' - ' + toYear + ')';

        if (numgroupsPatternsChart) numgroupsPatternsChart.destroy();
        numgroupsPatternsChart = new Chart(document.getElementById('numgroups-patterns-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: barColors,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Count: ' + ctx.raw + ' (' + pcts[ctx.dataIndex] + '%)'
                        }
                    },
                    title: {
                        display: true,
                        text: [titlePatterns, 'Color: green = 5 groups, blue = 4, orange = 3, red = 2 or fewer'],
                        font: { size: 14 },
                    },
                },
                scales: {
                    x: { title: { display: true, text: 'Count' }, beginAtZero: true },
                    y: { ticks: { font: { size: 11 } } },
                }
            }
        });
    }

    function updateNumGroupsTimeline() {
        const range = parseInt(document.getElementById('numgroups-range').value);
        let data = templatesOcc;
        if (range > 0) {
            data = data.slice(-range);
        }

        const labels = data.map(d => d.date);
        const spreads = data.map(d => d.spread);

        const window = 20;
        const rolling = spreads.map((_, i) => {
            const start = Math.max(0, i - window + 1);
            const slice = spreads.slice(start, i + 1);
            return slice.reduce((a, b) => a + b, 0) / slice.length;
        });

        if (numgroupsTimelineChart) numgroupsTimelineChart.destroy();
        numgroupsTimelineChart = new Chart(document.getElementById('numgroups-timeline-chart'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Decades covered per draw',
                        data: spreads,
                        borderColor: '#911eb444',
                        backgroundColor: '#911eb422',
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: true,
                    },
                    {
                        label: 'Rolling avg (20 draws)',
                        data: rolling,
                        borderColor: '#e6194b',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 0,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { font: { size: 12 } } },
                    title: { display: true, text: 'Decade Spread Over Time', font: { size: 16 } },
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Draw date' },
                        ticks: { maxTicksLimit: 15, maxRotation: 45 },
                    },
                    y: {
                        title: { display: true, text: 'Decades covered' },
                        min: 0, max: 5,
                    }
                }
            }
        });
    }

    updateNumGroupsCharts();
    updateNumGroupsTimeline();
"""


def _page_sumrange_content():
    return """\
            <h2>Sum Range</h2>
            <p style="font-size: 13px; color: #888; margin-bottom: 15px;">
                Sum of the 6 drawn numbers per draw. Theoretical range: 21 (1+2+3+4+5+6) to 279 (44+45+46+47+48+49). Most draws cluster around 140-160.
            </p>

            <div class="controls">
                <label>From:</label>
                <select id="sumrange-from-year"></select>
                <label>To:</label>
                <select id="sumrange-to-year"></select>
            </div>

            <div class="chart-container">
                <canvas id="sumrange-dist-chart"></canvas>
            </div>

            <div class="controls">
                <label>Timeline - show last:</label>
                <select id="sumrange-range">
                    <option value="50">50 draws</option>
                    <option value="100">100 draws</option>
                    <option value="200">200 draws</option>
                    <option value="500">500 draws</option>
                    <option value="0" selected>All draws</option>
                </select>
            </div>

            <div class="chart-container" style="height: 400px;">
                <canvas id="sumrange-timeline-chart"></canvas>
            </div>
"""


def _page_sumrange_js():
    return """\
    let sumrangeDistChart = null;
    let sumrangeTimelineChart = null;

    const fromSelect = document.getElementById('sumrange-from-year');
    const toSelect = document.getElementById('sumrange-to-year');
    const srYears = [...new Set(sumrangeOcc.map(d => d.date.split('-')[0]))].sort();
    srYears.forEach(y => {
        fromSelect.add(new Option(y, y));
        toSelect.add(new Option(y, y));
    });
    fromSelect.value = srYears[0];
    toSelect.value = srYears[srYears.length - 1];

    fromSelect.addEventListener('change', updateSumRangeDist);
    toSelect.addEventListener('change', updateSumRangeDist);
    document.getElementById('sumrange-range').addEventListener('change', updateSumRangeTimeline);

    function updateSumRangeDist() {
        const fromYear = document.getElementById('sumrange-from-year').value;
        const toYear = document.getElementById('sumrange-to-year').value;

        const filtered = sumrangeOcc.filter(d => {
            const y = d.date.split('-')[0];
            return y >= fromYear && y <= toYear;
        });

        const total = filtered.length;

        // bin sums into ranges of 10
        const bins = {};
        filtered.forEach(d => {
            const bin = Math.floor(d.sum / 10) * 10;
            bins[bin] = (bins[bin] || 0) + 1;
        });

        const binKeys = Object.keys(bins).map(Number).sort((a, b) => a - b);
        const labels = binKeys.map(k => k + '-' + (k + 9));
        const counts = binKeys.map(k => bins[k]);
        const pcts = counts.map(c => ((c / total) * 100).toFixed(1));

        // compute mean
        const mean = filtered.reduce((acc, d) => acc + d.sum, 0) / total;

        // color: highlight the bins around the mean
        const barColors = binKeys.map(k => {
            const mid = k + 5;
            const dist = Math.abs(mid - mean);
            if (dist <= 15) return '#3cb44b';
            if (dist <= 35) return '#4363d8';
            return '#e6194b88';
        });

        const titleText = 'Sum Distribution (' + fromYear + ' - ' + toYear + ', ' + total + ' draws, mean: ' + mean.toFixed(1) + ')';

        if (sumrangeDistChart) sumrangeDistChart.destroy();
        sumrangeDistChart = new Chart(document.getElementById('sumrange-dist-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: barColors,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Count: ' + ctx.raw + ' (' + pcts[ctx.dataIndex] + '%)'
                        }
                    },
                    title: { display: true, text: titleText, font: { size: 16 } },
                },
                scales: {
                    x: { title: { display: true, text: 'Sum range' } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                }
            }
        });
    }

    function updateSumRangeTimeline() {
        const range = parseInt(document.getElementById('sumrange-range').value);
        let data = sumrangeOcc;
        if (range > 0) {
            data = data.slice(-range);
        }

        const labels = data.map(d => d.date);
        const sums = data.map(d => d.sum);

        // rolling average
        const window = 20;
        const rolling = sums.map((_, i) => {
            const start = Math.max(0, i - window + 1);
            const slice = sums.slice(start, i + 1);
            return slice.reduce((a, b) => a + b, 0) / slice.length;
        });

        // overall mean
        const mean = sums.reduce((a, b) => a + b, 0) / sums.length;

        if (sumrangeTimelineChart) sumrangeTimelineChart.destroy();
        sumrangeTimelineChart = new Chart(document.getElementById('sumrange-timeline-chart'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Sum per draw',
                        data: sums,
                        borderColor: '#3cb44b44',
                        backgroundColor: '#3cb44b22',
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: true,
                    },
                    {
                        label: 'Rolling avg (20 draws)',
                        data: rolling,
                        borderColor: '#e6194b',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 0,
                    },
                    {
                        label: 'Mean (' + mean.toFixed(1) + ')',
                        data: Array(data.length).fill(mean),
                        borderColor: '#88888866',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { font: { size: 12 } } },
                    title: { display: true, text: 'Sum per Draw Over Time', font: { size: 16 } },
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Draw date' },
                        ticks: { maxTicksLimit: 15, maxRotation: 45 },
                    },
                    y: {
                        title: { display: true, text: 'Sum' },
                    }
                }
            }
        });
    }

    updateSumRangeDist();
    updateSumRangeTimeline();
"""


def _page_distance_content():
    return """\
            <h2>Recency Score</h2>
            <p style="font-size: 13px; color: #888; margin-bottom: 15px;">
                For each draw, sum the gaps (draws since last appearance) of all 6 numbers.
                Low score = numbers appeared recently. High score = numbers haven't been drawn in a while.
            </p>

            <div class="chart-container">
                <canvas id="distance-dist-chart"></canvas>
            </div>

            <div class="controls">
                <label>Timeline - show last:</label>
                <select id="distance-range">
                    <option value="50">50 draws</option>
                    <option value="100">100 draws</option>
                    <option value="200">200 draws</option>
                    <option value="500">500 draws</option>
                    <option value="0" selected>All draws</option>
                </select>
            </div>

            <div class="chart-container" style="height: 400px;">
                <canvas id="distance-timeline-chart"></canvas>
            </div>
"""


def _page_distance_js():
    return """\
    let distanceDistChart = null;
    let distanceTimelineChart = null;

    function updateDistanceDist() {
        // bin scores into ranges of 5
        const bins = {};
        distanceFreq.forEach(d => {
            const bin = Math.floor(d.score / 5) * 5;
            bins[bin] = (bins[bin] || 0) + d.count;
        });

        const binKeys = Object.keys(bins).map(Number).sort((a, b) => a - b);
        const labels = binKeys.map(k => k + '-' + (k + 4));
        const counts = binKeys.map(k => bins[k]);
        const total = counts.reduce((a, b) => a + b, 0);
        const pcts = counts.map(c => ((c / total) * 100).toFixed(1));

        // find the peak bin
        const maxCount = Math.max(...counts);
        const peakBin = binKeys[counts.indexOf(maxCount)];

        const barColors = binKeys.map(k => {
            const dist = Math.abs(k - peakBin);
            if (dist <= 10) return '#3cb44b';
            if (dist <= 25) return '#4363d8';
            return '#e6194b88';
        });

        if (distanceDistChart) distanceDistChart.destroy();
        distanceDistChart = new Chart(document.getElementById('distance-dist-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: barColors,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Count: ' + ctx.raw + ' (' + pcts[ctx.dataIndex] + '%)'
                        }
                    },
                    title: {
                        display: true,
                        text: ['Recency Score Distribution (' + total + ' draws)',
                               'Score = sum of gaps since each number last appeared'],
                        font: { size: 14 },
                    },
                },
                scales: {
                    x: { title: { display: true, text: 'Recency score (binned by 5)' } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                }
            }
        });
    }

    function updateDistanceTimeline() {
        const range = parseInt(document.getElementById('distance-range').value);
        // filter out draws with no score (early draws where not all numbers have been seen)
        let data = distanceScores.filter(d => d.score !== null);
        if (range > 0) {
            data = data.slice(-range);
        }

        const labels = data.map(d => d.date);
        const scores = data.map(d => d.score);

        const window = 20;
        const rolling = scores.map((_, i) => {
            const start = Math.max(0, i - window + 1);
            const slice = scores.slice(start, i + 1);
            return slice.reduce((a, b) => a + b, 0) / slice.length;
        });

        const mean = scores.reduce((a, b) => a + b, 0) / scores.length;

        if (distanceTimelineChart) distanceTimelineChart.destroy();
        distanceTimelineChart = new Chart(document.getElementById('distance-timeline-chart'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Recency score per draw',
                        data: scores,
                        borderColor: '#f5823144',
                        backgroundColor: '#f5823122',
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: true,
                    },
                    {
                        label: 'Rolling avg (20 draws)',
                        data: rolling,
                        borderColor: '#e6194b',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 0,
                    },
                    {
                        label: 'Mean (' + mean.toFixed(1) + ')',
                        data: Array(data.length).fill(mean),
                        borderColor: '#88888866',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { font: { size: 12 } } },
                    title: { display: true, text: 'Recency Score Over Time', font: { size: 16 } },
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Draw date' },
                        ticks: { maxTicksLimit: 15, maxRotation: 45 },
                    },
                    y: {
                        title: { display: true, text: 'Recency score' },
                    }
                }
            }
        });
    }

    document.getElementById('distance-range').addEventListener('change', updateDistanceTimeline);
    updateDistanceDist();
    updateDistanceTimeline();
"""


def _page_consecutive_content():
    return """\
            <h2>Consecutive Pairs</h2>
            <p style="font-size: 13px; color: #888; margin-bottom: 15px;">
                Count of consecutive number pairs per draw (e.g. 12-13, 25-26). Most draws have 0 or 1 consecutive pair.
            </p>

            <div class="controls">
                <label>From:</label>
                <select id="consec-from-year"></select>
                <label>To:</label>
                <select id="consec-to-year"></select>
            </div>

            <div class="chart-container">
                <canvas id="consec-freq-chart"></canvas>
            </div>

            <div class="chart-container" style="height: 500px;">
                <canvas id="consec-pairs-chart"></canvas>
            </div>

            <div class="chart-container">
                <canvas id="consec-decade-chart"></canvas>
            </div>
"""


def _page_consecutive_js():
    return """\
    let consecFreqChart = null;
    let consecPairsChart = null;
    let consecDecadeChart = null;

    const fromSelect = document.getElementById('consec-from-year');
    const toSelect = document.getElementById('consec-to-year');
    const cYears = [...new Set(consecutiveOcc.map(d => d.date.split('-')[0]))].sort();
    cYears.forEach(y => {
        fromSelect.add(new Option(y, y));
        toSelect.add(new Option(y, y));
    });
    fromSelect.value = cYears[0];
    toSelect.value = cYears[cYears.length - 1];

    fromSelect.addEventListener('change', updateConsecCharts);
    toSelect.addEventListener('change', updateConsecCharts);

    function updateConsecCharts() {
        updateConsecFreqChart();
        updateConsecPairsChart();
        updateConsecDecadeChart();
    }

    function updateConsecFreqChart() {
        const fromYear = document.getElementById('consec-from-year').value;
        const toYear = document.getElementById('consec-to-year').value;

        const filtered = consecutiveOcc.filter(d => {
            const y = d.date.split('-')[0];
            return y >= fromYear && y <= toYear;
        });

        const total = filtered.length;
        const pairCounts = {};
        filtered.forEach(d => {
            pairCounts[d.pairs] = (pairCounts[d.pairs] || 0) + 1;
        });

        const keys = Object.keys(pairCounts).map(Number).sort();
        const labels = keys.map(k => k + ' pair' + (k !== 1 ? 's' : ''));
        const counts = keys.map(k => pairCounts[k]);
        const pcts = counts.map(c => ((c / total) * 100).toFixed(1));

        const barColors = keys.map(k => {
            if (k === 0) return '#3cb44b';
            if (k === 1) return '#4363d8';
            if (k === 2) return '#f58231';
            return '#e6194b';
        });

        const titleText = 'Consecutive Pairs Distribution (' + fromYear + ' - ' + toYear + ', ' + total + ' draws)';

        if (consecFreqChart) consecFreqChart.destroy();
        consecFreqChart = new Chart(document.getElementById('consec-freq-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: barColors,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Count: ' + ctx.raw + ' (' + pcts[ctx.dataIndex] + '%)'
                        }
                    },
                    title: { display: true, text: titleText, font: { size: 16 } },
                },
                scales: {
                    x: { title: { display: true, text: 'Consecutive pairs' } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                }
            }
        });
    }

    function getConsecFiltered() {
        const fromYear = document.getElementById('consec-from-year').value;
        const toYear = document.getElementById('consec-to-year').value;
        return consecutiveOcc.filter(d => {
            const y = d.date.split('-')[0];
            return y >= fromYear && y <= toYear;
        });
    }

    function updateConsecPairsChart() {
        const filtered = getConsecFiltered();
        const fromYear = document.getElementById('consec-from-year').value;
        const toYear = document.getElementById('consec-to-year').value;

        // count each specific pair
        const pairCounts = {};
        filtered.forEach(d => {
            d.consec_pairs.forEach(p => {
                pairCounts[p] = (pairCounts[p] || 0) + 1;
            });
        });

        const sorted = Object.entries(pairCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 25);

        const labels = sorted.map(([k, _]) => k);
        const counts = sorted.map(([_, c]) => c);
        const total = filtered.filter(d => d.pairs > 0).length;

        // color by decade of the lower number
        const barColors = sorted.map(([k, _]) => {
            const lower = parseInt(k.split('-')[0]);
            if (lower <= 9) return '#e6194b';
            if (lower <= 19) return '#3cb44b';
            if (lower <= 29) return '#4363d8';
            if (lower <= 39) return '#f58231';
            return '#911eb4';
        });

        if (consecPairsChart) consecPairsChart.destroy();
        consecPairsChart = new Chart(document.getElementById('consec-pairs-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: barColors,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Appeared together ' + ctx.raw + ' times'
                        }
                    },
                    title: {
                        display: true,
                        text: ['Top 25 Most Common Consecutive Pairs (' + fromYear + ' - ' + toYear + ')',
                               'Color by decade: red=1-9, green=10-19, blue=20-29, orange=30-39, purple=40-49'],
                        font: { size: 14 },
                    },
                },
                scales: {
                    x: { title: { display: true, text: 'Count' }, beginAtZero: true },
                    y: { ticks: { font: { size: 12 } } },
                }
            }
        });
    }

    function updateConsecDecadeChart() {
        const filtered = getConsecFiltered();
        const fromYear = document.getElementById('consec-from-year').value;
        const toYear = document.getElementById('consec-to-year').value;

        // count pairs by decade group of the lower number
        const decadeCounts = [0, 0, 0, 0, 0];
        filtered.forEach(d => {
            d.consec_pairs.forEach(p => {
                const lower = parseInt(p.split('-')[0]);
                if (lower <= 9) decadeCounts[0]++;
                else if (lower <= 19) decadeCounts[1]++;
                else if (lower <= 29) decadeCounts[2]++;
                else if (lower <= 39) decadeCounts[3]++;
                else decadeCounts[4]++;
            });
        });

        const total = decadeCounts.reduce((a, b) => a + b, 0);
        const pcts = decadeCounts.map(c => total > 0 ? ((c / total) * 100).toFixed(1) : '0.0');

        if (consecDecadeChart) consecDecadeChart.destroy();
        consecDecadeChart = new Chart(document.getElementById('consec-decade-chart'), {
            type: 'bar',
            data: {
                labels: ['1-9', '10-19', '20-29', '30-39', '40-49'],
                datasets: [{
                    label: 'Count',
                    data: decadeCounts,
                    backgroundColor: ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4'],
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => 'Count: ' + ctx.raw + ' (' + pcts[ctx.dataIndex] + '%)'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Consecutive Pairs by Decade Group (' + fromYear + ' - ' + toYear + ', ' + total + ' total pairs)',
                        font: { size: 16 },
                    },
                },
                scales: {
                    x: { title: { display: true, text: 'Decade group (of lower number)' } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                }
            }
        });
    }

    updateConsecCharts();
"""


def _page_hotcold_content():
    return """\
            <h2>Number Frequency</h2>
            <p style="font-size: 13px; color: #888; margin-bottom: 15px;">
                Per-number frequency across all draws and recent windows. This is descriptive, not predictive &mdash; past frequency does not indicate future likelihood.
            </p>

            <div class="controls">
                <label>Sort by:</label>
                <select id="hotcold-sort">
                    <option value="number">Number (1-49)</option>
                    <option value="total" selected>Total count</option>
                    <option value="rate_20">Last 20 draws</option>
                    <option value="rate_50">Last 50 draws</option>
                    <option value="rate_100">Last 100 draws</option>
                    <option value="deviation">Deviation (last 50 vs overall)</option>
                </select>
            </div>

            <div class="chart-container" style="height: 600px;">
                <canvas id="hotcold-freq-chart"></canvas>
            </div>

            <div class="chart-container" style="height: 500px;">
                <canvas id="hotcold-compare-chart"></canvas>
            </div>

            <div class="chart-container" style="height: 400px;">
                <canvas id="hotcold-deviation-chart"></canvas>
            </div>

            <div id="hotcold-heatmap-container" style="background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; overflow-x: auto;">
                <h3 style="font-size: 16px; margin-bottom: 5px; color: #1a1a2e;">Yearly Frequency Heatmap</h3>
                <p style="font-size: 12px; color: #888; margin-bottom: 10px;">Green = drawn often, Red = drawn rarely</p>
                <div id="hotcold-heatmap"></div>
            </div>
"""


def _page_hotcold_js():
    return """\
    let hotcoldFreqChart = null;
    let hotcoldCompareChart = null;
    let hotcoldDeviationChart = null;

    document.getElementById('hotcold-sort').addEventListener('change', updateHotColdCharts);

    function getSortedNumbers(sortBy) {
        const nums = Object.keys(hotcoldFreq).map(Number);
        if (sortBy === 'number') return nums.sort((a, b) => a - b);
        if (sortBy === 'total') return nums.sort((a, b) => hotcoldFreq[b].total - hotcoldFreq[a].total);
        if (sortBy === 'rate_20') return nums.sort((a, b) => hotcoldFreq[b].rate_20 - hotcoldFreq[a].rate_20);
        if (sortBy === 'rate_50') return nums.sort((a, b) => hotcoldFreq[b].rate_50 - hotcoldFreq[a].rate_50);
        if (sortBy === 'rate_100') return nums.sort((a, b) => hotcoldFreq[b].rate_100 - hotcoldFreq[a].rate_100);
        if (sortBy === 'deviation') {
            return nums.sort((a, b) => {
                const devA = hotcoldFreq[a].rate_all > 0 ? hotcoldFreq[a].rate_50 / hotcoldFreq[a].rate_all : 0;
                const devB = hotcoldFreq[b].rate_all > 0 ? hotcoldFreq[b].rate_50 / hotcoldFreq[b].rate_all : 0;
                return devB - devA;
            });
        }
        return nums;
    }

    function updateHotColdCharts() {
        const sortBy = document.getElementById('hotcold-sort').value;
        const sorted = getSortedNumbers(sortBy);

        // expected rate (uniform: 6 numbers from 49)
        const expectedRate = 6 / 49;

        // Chart 1: Overall frequency bar
        const labels = sorted.map(n => 'Nr ' + n);
        const totals = sorted.map(n => hotcoldFreq[n].total);

        const freqColors = sorted.map(n => {
            const t = hotcoldFreq[n].trend;
            if (t === 'hot') return '#e6194b';
            if (t === 'cold') return '#4363d8';
            return '#3cb44b';
        });

        if (hotcoldFreqChart) hotcoldFreqChart.destroy();
        hotcoldFreqChart = new Chart(document.getElementById('hotcold-freq-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Total draws',
                    data: totals,
                    backgroundColor: freqColors,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const n = sorted[ctx.dataIndex];
                                const d = hotcoldFreq[n];
                                return [
                                    'Total: ' + d.total,
                                    'Rate: ' + (d.rate_all * 100).toFixed(1) + '%',
                                    'Trend: ' + d.trend
                                ];
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: ['Overall Frequency (all numbers)',
                               'Red = hot (last 50 > 115% of overall), Blue = cold (< 85%), Green = neutral'],
                        font: { size: 14 },
                    },
                },
                scales: {
                    x: { ticks: { maxRotation: 90, font: { size: 10 } } },
                    y: { title: { display: true, text: 'Total count' }, beginAtZero: true },
                }
            }
        });

        // Chart 2: Rate comparison (overall vs last 50)
        const ratesAll = sorted.map(n => (hotcoldFreq[n].rate_all * 100));
        const rates50 = sorted.map(n => (hotcoldFreq[n].rate_50 * 100));
        const rates20 = sorted.map(n => (hotcoldFreq[n].rate_20 * 100));

        if (hotcoldCompareChart) hotcoldCompareChart.destroy();
        hotcoldCompareChart = new Chart(document.getElementById('hotcold-compare-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Overall rate %',
                        data: ratesAll,
                        backgroundColor: '#3cb44b88',
                    },
                    {
                        label: 'Last 50 draws %',
                        data: rates50,
                        backgroundColor: '#4363d888',
                    },
                    {
                        label: 'Last 20 draws %',
                        data: rates20,
                        backgroundColor: '#e6194b88',
                    },
                    {
                        label: 'Expected (' + (expectedRate * 100).toFixed(1) + '%)',
                        data: Array(sorted.length).fill(expectedRate * 100),
                        type: 'line',
                        borderColor: '#88888866',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { font: { size: 12 } } },
                    title: {
                        display: true,
                        text: 'Rate Comparison: Overall vs Recent Windows',
                        font: { size: 16 },
                    },
                },
                scales: {
                    x: { ticks: { maxRotation: 90, font: { size: 10 } } },
                    y: { title: { display: true, text: 'Appearance rate %' }, beginAtZero: true },
                }
            }
        });

        // Chart 3: Deviation (last 50 rate / overall rate)
        const deviations = sorted.map(n => {
            const d = hotcoldFreq[n];
            return d.rate_all > 0 ? ((d.rate_50 / d.rate_all - 1) * 100) : 0;
        });

        const devColors = deviations.map(d => {
            if (d > 15) return '#e6194b';
            if (d < -15) return '#4363d8';
            return '#3cb44b';
        });

        if (hotcoldDeviationChart) hotcoldDeviationChart.destroy();
        hotcoldDeviationChart = new Chart(document.getElementById('hotcold-deviation-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Deviation %',
                        data: deviations,
                        backgroundColor: devColors,
                    },
                    {
                        label: 'Baseline (0%)',
                        data: Array(sorted.length).fill(0),
                        type: 'line',
                        borderColor: '#888888',
                        borderWidth: 1,
                        pointRadius: 0,
                        fill: false,
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                if (ctx.datasetIndex === 1) return '';
                                const n = sorted[ctx.dataIndex];
                                const d = hotcoldFreq[n];
                                return [
                                    'Deviation: ' + ctx.raw.toFixed(1) + '%',
                                    'Overall: ' + (d.rate_all * 100).toFixed(1) + '%',
                                    'Last 50: ' + (d.rate_50 * 100).toFixed(1) + '%'
                                ];
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: ['Deviation: Last 50 Draws vs Overall Rate',
                               'Red = hot (>+15%), Blue = cold (<-15%), Green = neutral'],
                        font: { size: 14 },
                    },
                },
                scales: {
                    x: { ticks: { maxRotation: 90, font: { size: 10 } } },
                    y: { title: { display: true, text: 'Deviation %' } },
                }
            }
        });
    }

    // --- Yearly heatmap (HTML table) ---
    function updateHeatmap() {
        const nums = Array.from({length: 49}, (_, i) => i + 1);

        // find min/max for color scale
        let minVal = Infinity, maxVal = 0;
        nums.forEach(n => {
            yearlyYears.forEach(y => {
                const v = yearlyData[n] ? (yearlyData[n][y] || 0) : 0;
                if (v < minVal) minVal = v;
                if (v > maxVal) maxVal = v;
            });
        });

        let html = '<table style="border-collapse: collapse; font-size: 11px; width: 100%;">';
        // header
        html += '<tr><th style="padding: 3px 6px; position: sticky; left: 0; background: #fff;">Nr</th>';
        yearlyYears.forEach(y => {
            html += '<th style="padding: 3px 4px; writing-mode: vertical-lr; text-orientation: mixed; height: 50px;">' + y + '</th>';
        });
        html += '</tr>';

        // rows
        nums.forEach(n => {
            html += '<tr><td style="padding: 2px 6px; font-weight: bold; position: sticky; left: 0; background: #fff;">' + n + '</td>';
            yearlyYears.forEach(y => {
                const v = yearlyData[n] ? (yearlyData[n][y] || 0) : 0;
                const ratio = maxVal > minVal ? (v - minVal) / (maxVal - minVal) : 0;
                const r = Math.round(220 - 170 * ratio);
                const g = Math.round(80 + 140 * ratio);
                const b = Math.round(80);
                html += '<td style="padding: 2px; text-align: center; background: rgb(' + r + ',' + g + ',' + b + '); color: ' + (ratio > 0.5 ? '#fff' : '#333') + ';" title="Nr ' + n + ' in ' + y + ': ' + v + 'x">' + v + '</td>';
            });
            html += '</tr>';
        });
        html += '</table>';

        document.getElementById('hotcold-heatmap').innerHTML = html;
    }

    updateHotColdCharts();
    updateHeatmap();
"""


def _page_gaps_content():
    return """\
            <h2>Number Gaps</h2>
            <p style="font-size: 13px; color: #888; margin-bottom: 15px;">
                Gap = number of draws since a number last appeared. Large gaps mean the number hasn't been drawn recently.
            </p>

            <div class="controls">
                <label>Sort by:</label>
                <select id="gaps-sort">
                    <option value="current" selected>Current gap (largest first)</option>
                    <option value="number">Number (1-49)</option>
                    <option value="avg">Average gap</option>
                    <option value="max">Max gap</option>
                </select>
            </div>

            <div class="chart-container" style="height: 600px;">
                <canvas id="gaps-current-chart"></canvas>
            </div>

            <div class="chart-container" style="height: 500px;">
                <canvas id="gaps-comparison-chart"></canvas>
            </div>
"""


def _page_gaps_js():
    return """\
    let gapsCurrentChart = null;
    let gapsComparisonChart = null;

    document.getElementById('gaps-sort').addEventListener('change', updateGapsCharts);

    function getGapsSorted(sortBy) {
        const nums = Object.keys(gapData).map(Number);
        if (sortBy === 'number') return nums.sort((a, b) => a - b);
        if (sortBy === 'current') return nums.sort((a, b) => gapData[b].current_gap - gapData[a].current_gap);
        if (sortBy === 'avg') return nums.sort((a, b) => gapData[b].avg_gap - gapData[a].avg_gap);
        if (sortBy === 'max') return nums.sort((a, b) => gapData[b].max_gap - gapData[a].max_gap);
        return nums;
    }

    function updateGapsCharts() {
        const sortBy = document.getElementById('gaps-sort').value;
        const sorted = getGapsSorted(sortBy);
        const labels = sorted.map(n => 'Nr ' + n);

        // current gap bar chart
        const currentGaps = sorted.map(n => gapData[n].current_gap);
        const avgGaps = sorted.map(n => gapData[n].avg_gap);

        // color: red if current gap > 1.5x average, green if below average
        const barColors = sorted.map(n => {
            const g = gapData[n];
            if (g.avg_gap > 0) {
                const ratio = g.current_gap / g.avg_gap;
                if (ratio > 1.5) return '#e6194b';
                if (ratio > 1.0) return '#f58231';
                return '#3cb44b';
            }
            return '#888888';
        });

        if (gapsCurrentChart) gapsCurrentChart.destroy();
        gapsCurrentChart = new Chart(document.getElementById('gaps-current-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Current gap',
                        data: currentGaps,
                        backgroundColor: barColors,
                    },
                    {
                        label: 'Average gap',
                        data: avgGaps,
                        type: 'line',
                        borderColor: '#4363d8',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: '#4363d8',
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' },
                    title: {
                        display: true,
                        text: ['Current Gap vs Average Gap (draws since last appearance)',
                               'Red = well above average, Orange = above, Green = at or below average'],
                        font: { size: 14 },
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: (ctx) => {
                                if (ctx.datasetIndex > 0) return '';
                                const n = sorted[ctx.dataIndex];
                                const g = gapData[n];
                                return 'Avg: ' + g.avg_gap.toFixed(1) + ', Max: ' + g.max_gap + ', Total: ' + g.total_appearances;
                            }
                        }
                    },
                },
                scales: {
                    x: { ticks: { maxRotation: 90, font: { size: 10 } } },
                    y: { title: { display: true, text: 'Draws since last appearance' }, beginAtZero: true },
                }
            }
        });

        // comparison: current gap, avg gap, max gap side by side
        const maxGaps = sorted.map(n => gapData[n].max_gap);

        if (gapsComparisonChart) gapsComparisonChart.destroy();
        gapsComparisonChart = new Chart(document.getElementById('gaps-comparison-chart'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Current',
                        data: currentGaps,
                        backgroundColor: '#e6194b88',
                    },
                    {
                        label: 'Average',
                        data: avgGaps,
                        backgroundColor: '#3cb44b88',
                    },
                    {
                        label: 'Maximum',
                        data: maxGaps,
                        backgroundColor: '#4363d844',
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' },
                    title: {
                        display: true,
                        text: 'Gap Comparison: Current vs Average vs Maximum',
                        font: { size: 16 },
                    },
                },
                scales: {
                    x: { ticks: { maxRotation: 90, font: { size: 10 } } },
                    y: { title: { display: true, text: 'Gap (draws)' }, beginAtZero: true },
                }
            }
        });
    }

    updateGapsCharts();
"""


# ---------------------------------------------------------------------------
# HTML page template builder
# ---------------------------------------------------------------------------

def _build_page(page_id, title, content_html, page_js):
    """Build a complete HTML page."""
    return """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SELMA - """ + title + """</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="css/style.css">
</head>
<body data-page=\"""" + page_id + """\">
    <div class="sidebar" id="sidebar"></div>

    <div class="main">
""" + content_html + """\
    </div>

    <script src="js/data.js"></script>
    <script src="js/sidebar.js"></script>
    <script>
""" + page_js + """\
    </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_html():
    """Generate multi-page static site in docs/."""
    print("##### Generate Visualization #####")

    # Load all data
    profile_data, years, year_draw_counts = load_profile_data()
    oddeven_freq, oddeven_occ = load_oddeven_data()
    templates_occ = load_templates_data()
    sumrange_occ = load_sumrange_data()
    distance_freq, distance_scores = load_distance_data()
    consecutive_occ = load_consecutive_data()
    hotcold_freq = load_hotcold_data()
    yearly_data, yearly_years = load_yearly_data()
    gap_data, gap_total_draws = load_gap_data()
    draws_data = load_draws_data()

    # Create directory structure
    os.makedirs(os.path.join(DOCS_DIR, "css"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "js"), exist_ok=True)

    # Write shared CSS
    css_path = os.path.join(DOCS_DIR, "css", "style.css")
    with open(css_path, "w") as f:
        f.write(SHARED_CSS)
    print("  Written: " + css_path)

    # Write shared sidebar JS
    sidebar_path = os.path.join(DOCS_DIR, "js", "sidebar.js")
    with open(sidebar_path, "w") as f:
        f.write(SIDEBAR_JS)
    print("  Written: " + sidebar_path)

    # Write data JS
    data_js = ""
    data_js += "const profileData = " + json.dumps(profile_data) + ";\n"
    data_js += "const years = " + json.dumps(years) + ";\n"
    data_js += "const yearDrawCounts = " + json.dumps(year_draw_counts) + ";\n"
    data_js += "const oddevenFreq = " + json.dumps(oddeven_freq) + ";\n"
    data_js += "const oddevenOcc = " + json.dumps(oddeven_occ) + ";\n"
    data_js += "const templatesOcc = " + json.dumps(templates_occ) + ";\n"
    data_js += "const sumrangeOcc = " + json.dumps(sumrange_occ) + ";\n"
    data_js += "const distanceFreq = " + json.dumps(distance_freq) + ";\n"
    data_js += "const distanceScores = " + json.dumps(distance_scores) + ";\n"
    data_js += "const consecutiveOcc = " + json.dumps(consecutive_occ) + ";\n"
    data_js += "const hotcoldFreq = " + json.dumps(hotcold_freq) + ";\n"
    data_js += "const yearlyData = " + json.dumps(yearly_data) + ";\n"
    data_js += "const yearlyYears = " + json.dumps(yearly_years) + ";\n"
    data_js += "const gapData = " + json.dumps(gap_data) + ";\n"
    data_js += "const gapTotalDraws = " + json.dumps(gap_total_draws) + ";\n"
    data_js += "const drawsData = " + json.dumps(draws_data) + ";\n"

    data_path = os.path.join(DOCS_DIR, "js", "data.js")
    with open(data_path, "w") as f:
        f.write(data_js)
    print("  Written: " + data_path)

    # Define pages: (filename, page_id, title, content_fn, js_fn)
    pages = [
        ("index.html",       "drawhistory",  "Draw History",       _page_drawhistory_content,  _page_drawhistory_js),
        ("profiles.html",    "profiles",     "Profiles",           _page_profiles_content,     _page_profiles_js),
        ("oddeven.html",     "oddeven",      "Odd / Even",         _page_oddeven_content,      _page_oddeven_js),
        ("numgroups.html",   "numgroups",    "Number Groups",      _page_numgroups_content,    _page_numgroups_js),
        ("sumrange.html",    "sumrange",     "Sum Range",          _page_sumrange_content,     _page_sumrange_js),
        ("distance.html",    "distance",     "Recency",            _page_distance_content,     _page_distance_js),
        ("consecutive.html", "consecutive",  "Consecutive",        _page_consecutive_content,  _page_consecutive_js),
        ("hotcold.html",     "hotcold",      "Hot / Cold",         _page_hotcold_content,      _page_hotcold_js),
        ("gaps.html",        "gaps",         "Gaps",               _page_gaps_content,         _page_gaps_js),
    ]

    for filename, page_id, title, content_fn, js_fn in pages:
        html = _build_page(page_id, title, content_fn(), js_fn())
        page_path = os.path.join(DOCS_DIR, filename)
        with open(page_path, "w") as f:
            f.write(html)
        print("  Written: " + page_path)

    print("Site generated in " + DOCS_DIR)
    print("Open in browser: file://" + os.path.join(DOCS_DIR, "index.html"))
