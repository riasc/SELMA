import os

from selma.config import COLLECT_DIR

PROFILES_DIR = os.path.join(COLLECT_DIR, "profiles")


class Profiles:
    def __init__(self, matrix, data, from_date=None):
        """Collect per-number, per-year trajectory profiles."""
        print("\tcollect Profiles")

        # filter by from_date
        if from_date:
            start = next((i for i, d in enumerate(data) if d >= from_date), 0)
        else:
            start = 0

        mat = matrix[start:]
        dat = data[start:]

        # group draws by year, track draw-in-year index
        year_draws = {}  # year -> list of dates
        for d in dat:
            year = d.split("-")[0]
            if year not in year_draws:
                year_draws[year] = []
            year_draws[year].append(d)

        # per-number, per-year: which draw_in_year it appeared
        # occurrence[number][year] = [draw_in_year indices]
        self.occurrence = {}
        for num in range(1, 50):
            self.occurrence[num] = {}
            for year in year_draws:
                self.occurrence[num][year] = []

        draw_idx = 0
        current_year = None
        draw_in_year = 0
        for x in range(0, mat.shape[0]):
            year = dat[x].split("-")[0]
            if year != current_year:
                current_year = year
                draw_in_year = 0
            else:
                draw_in_year += 1

            for idx, val in enumerate(mat[x]):
                if idx < 6:
                    num = int(val)
                    self.occurrence[num][year].append(draw_in_year)

        self.years = sorted(year_draws.keys())
        self.year_draw_counts = {y: len(year_draws[y]) for y in year_draws}

        self._save()

    def _save(self):
        if not os.path.exists(PROFILES_DIR):
            os.makedirs(PROFILES_DIR)

        # save per-number occurrence within each year
        with open(os.path.join(PROFILES_DIR, "occurrence.tsv"), "w") as f:
            f.write("# Per-number, per-year: which draws within the year the number appeared\n")
            f.write("# draw_in_year is 0-indexed within each year\n")
            f.write("number\tyear\tdraw_in_year\n")
            for num in range(1, 50):
                for year in self.years:
                    draws = self.occurrence[num][year]
                    if draws:
                        f.write(str(num) + "\t" + year + "\t" + "\t".join(str(d) for d in draws) + "\n")

        # save cumulative profiles: for each number+year, cumulative count at each draw
        with open(os.path.join(PROFILES_DIR, "cumulative.tsv"), "w") as f:
            f.write("# Cumulative draw count per number at each draw within the year\n")
            f.write("# Each value shows total times the number had been drawn by that draw_in_year\n")
            f.write("number\tyear\ttotal_draws_in_year\tcumulative_counts\n")
            for num in range(1, 50):
                for year in self.years:
                    total = self.year_draw_counts[year]
                    draws = set(self.occurrence[num][year])
                    cumulative = []
                    count = 0
                    for d in range(total):
                        if d in draws:
                            count += 1
                        cumulative.append(count)
                    f.write(str(num) + "\t" + year + "\t" + str(total) + "\t")
                    f.write("\t".join(str(c) for c in cumulative) + "\n")

    @classmethod
    def load(cls):
        """Load profiles from collect/profiles/."""
        obj = cls.__new__(cls)
        obj.occurrence = {}
        obj.years = []
        obj.year_draw_counts = {}

        # load cumulative profiles
        obj.cumulative = {}  # cumulative[num][year] = [counts]
        with open(os.path.join(PROFILES_DIR, "cumulative.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("number"):
                    continue
                cells = line.split("\t")
                num = int(cells[0])
                year = cells[1]
                total = int(cells[2])
                counts = [int(c) for c in cells[3:]]

                if num not in obj.cumulative:
                    obj.cumulative[num] = {}
                obj.cumulative[num][year] = counts

                if year not in obj.years:
                    obj.years.append(year)
                obj.year_draw_counts[year] = total

        obj.years.sort()
        return obj
