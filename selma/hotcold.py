import os
import datetime as dt
from collections import OrderedDict

from selma.config import COLLECT_DIR

HOTCOLD_DIR = os.path.join(COLLECT_DIR, "hotcold")


class HotCold:
    def __init__(self, matrix, data, from_date=None):
        """Collect per-number frequencies: overall, rolling windows, per year, per day."""
        print("\tcollect HotCold")

        # filter data by from_date
        if from_date:
            start = next((i for i, d in enumerate(data) if d >= from_date), 0)
        else:
            start = 0

        self.matrix = matrix[start:]
        self.data = data[start:]
        tdraws = len(self.data)

        # per-number occurrence: which draw indices
        self.occurrence = {}
        for x in range(0, self.matrix.shape[0]):
            for idx, val in enumerate(self.matrix[x]):
                if idx < 6:
                    num = int(val)
                    if num not in self.occurrence:
                        self.occurrence[num] = []
                    self.occurrence[num].append(x)

        # overall + rolling window frequencies
        windows = [20, 50, 100]
        self.freq = OrderedDict()
        for num in range(1, 50):
            total = len(self.occurrence.get(num, []))
            rate_all = total / tdraws if tdraws > 0 else 0

            window_rates = {}
            for w in windows:
                if tdraws >= w:
                    count_w = sum(1 for i in self.occurrence.get(num, []) if i >= tdraws - w)
                    window_rates[w] = count_w / w
                else:
                    window_rates[w] = rate_all

            # trend: compare last 50 rate to overall
            trend_rate = window_rates.get(50, rate_all)
            if rate_all > 0:
                trend_ratio = trend_rate / rate_all
                if trend_ratio > 1.15:
                    trend = "hot"
                elif trend_ratio < 0.85:
                    trend = "cold"
                else:
                    trend = "neutral"
            else:
                trend = "cold"

            self.freq[num] = {
                "total": total,
                "rate_all": rate_all,
                "windows": window_rates,
                "trend": trend,
            }

        # per-year frequencies
        self.yearly = {}
        year_draws = {}
        for x in range(0, len(self.data)):
            year = self.data[x].split("-")[0]
            if year not in year_draws:
                year_draws[year] = 0
            year_draws[year] += 1

        for num in range(1, 50):
            self.yearly[num] = {}
            for year in year_draws:
                self.yearly[num][year] = 0

        for x in range(0, self.matrix.shape[0]):
            year = self.data[x].split("-")[0]
            for idx, val in enumerate(self.matrix[x]):
                if idx < 6:
                    num = int(val)
                    self.yearly[num][year] += 1

        self.year_draws = year_draws

        # per-day (Mi/Sa) frequencies
        self.daily = {}
        day_draws = {"Mi": 0, "Sa": 0}
        for x in range(0, len(self.data)):
            date = dt.datetime.strptime(self.data[x].strip(), "%Y-%m-%d")
            day = "Mi" if date.weekday() == 2 else "Sa"
            day_draws[day] += 1

        self.day_indices = {}
        for x in range(0, len(self.data)):
            date = dt.datetime.strptime(self.data[x].strip(), "%Y-%m-%d")
            day = "Mi" if date.weekday() == 2 else "Sa"
            self.day_indices[x] = day

        for num in range(1, 50):
            self.daily[num] = {"Mi": 0, "Sa": 0}

        for x in range(0, self.matrix.shape[0]):
            day = self.day_indices[x]
            for idx, val in enumerate(self.matrix[x]):
                if idx < 6:
                    num = int(val)
                    self.daily[num][day] += 1

        self.day_draws = day_draws
        self._save()

    def _save(self):
        if not os.path.exists(HOTCOLD_DIR):
            os.makedirs(HOTCOLD_DIR)

        # save occurrence
        with open(os.path.join(HOTCOLD_DIR, "occurrence.tsv"), "w") as f:
            f.write("# For each number (1-49), the draw indices where it appeared (within filtered range)\n")
            f.write("number\tdraw_indices\n")
            for num in sorted(self.occurrence):
                f.write(str(num) + "\t" + "\t".join(str(i) for i in self.occurrence[num]) + "\n")

        # save overall + rolling window frequencies
        with open(os.path.join(HOTCOLD_DIR, "frequency.tsv"), "w") as f:
            f.write("# Per-number frequency: overall and rolling windows (sorted by total descending)\n")
            f.write("# trend: hot (last50 > 115% of overall), cold (< 85%), neutral (in between)\n")
            f.write("number\ttotal\trate_all\trate_last20\trate_last50\trate_last100\ttrend\n")
            for num in sorted(self.freq, key=lambda n: self.freq[n]["total"], reverse=True):
                v = self.freq[num]
                f.write(str(num) + "\t")
                f.write(str(v["total"]) + "\t")
                f.write(f"{v['rate_all']:.4f}" + "\t")
                f.write(f"{v['windows'].get(20, 0):.4f}" + "\t")
                f.write(f"{v['windows'].get(50, 0):.4f}" + "\t")
                f.write(f"{v['windows'].get(100, 0):.4f}" + "\t")
                f.write(v["trend"] + "\n")

        # save per-year frequencies
        years = sorted(self.year_draws.keys())
        with open(os.path.join(HOTCOLD_DIR, "frequency_yearly.tsv"), "w") as f:
            f.write("# Per-number frequency broken down by year\n")
            f.write("# count columns show how many times the number was drawn that year\n")
            f.write("number\t" + "\t".join(years) + "\n")
            for num in range(1, 50):
                f.write(str(num))
                for year in years:
                    f.write("\t" + str(self.yearly[num].get(year, 0)))
                f.write("\n")

        # save per-day frequencies
        with open(os.path.join(HOTCOLD_DIR, "frequency_daily.tsv"), "w") as f:
            f.write("# Per-number frequency broken down by draw day (Mi=Wednesday, Sa=Saturday)\n")
            f.write("# total_Mi/total_Sa: total draws on that day, rate: count / total draws for that day\n")
            f.write(f"# total draws: Mi={self.day_draws['Mi']}, Sa={self.day_draws['Sa']}\n")
            f.write("number\tcount_Mi\trate_Mi\tcount_Sa\trate_Sa\n")
            for num in range(1, 50):
                mi = self.daily[num]["Mi"]
                sa = self.daily[num]["Sa"]
                rate_mi = mi / self.day_draws["Mi"] if self.day_draws["Mi"] > 0 else 0
                rate_sa = sa / self.day_draws["Sa"] if self.day_draws["Sa"] > 0 else 0
                f.write(str(num) + "\t" + str(mi) + "\t" + f"{rate_mi:.4f}" + "\t" + str(sa) + "\t" + f"{rate_sa:.4f}" + "\n")

    @classmethod
    def load(cls):
        """Load pre-computed frequency data from collect/hotcold/."""
        obj = cls.__new__(cls)
        obj.freq = OrderedDict()
        with open(os.path.join(HOTCOLD_DIR, "frequency.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("number"):
                    continue
                cells = line.split("\t")
                num = int(cells[0])
                obj.freq[num] = {
                    "total": int(cells[1]),
                    "rate_all": float(cells[2]),
                    "windows": {
                        20: float(cells[3]),
                        50: float(cells[4]),
                        100: float(cells[5]),
                    },
                    "trend": cells[6],
                }
        return obj
