import os
from collections import OrderedDict

from selma.config import COLLECT_DIR

DISTANCE_DIR = os.path.join(COLLECT_DIR, "distance")


class DrawDistance:
    def __init__(self, matrix, data, from_date=None):
        """Collect occurrences and compute frequencies, save to collect/distance/."""
        print("\tcollect DrawDistance")

        # collect per-number draw occurrences from all data
        self.occurrence = {}
        for x in range(0, matrix.shape[0]):
            for idx, val in enumerate(matrix[x]):
                if idx < 6:
                    if val in self.occurrence:
                        self.occurrence[val].append(x)
                    else:
                        self.occurrence[val] = [x]

        # compute per-draw recency scores and frequency distribution
        from_index = 0
        if from_date:
            if from_date in list(data):
                from_index = list(data).index(from_date)

        sumdist = {}
        last_seen = {}
        self.draw_scores = []  # per-draw: (date, score or None)

        for x in range(0, matrix.shape[0]):
            dists = []
            for idx, val in enumerate(matrix[x]):
                if idx < 6:
                    if val in last_seen:
                        dists.append(x - last_seen[val])
                    last_seen[val] = x

            score = sum(dists) if len(dists) == 6 else None
            self.draw_scores.append((data[x], score))

            # only count for frequency if in range
            if x >= from_index and score is not None:
                if score in sumdist:
                    sumdist[score] += 1
                else:
                    sumdist[score] = 1

        tdraws = sum(sumdist.values())
        sumdist = OrderedDict(sorted(sumdist.items(), key=lambda x: x[1], reverse=True))
        if tdraws > 0:
            for key in sumdist:
                sumdist[key] = [sumdist[key], sumdist[key] / tdraws]

        self.distance = sumdist
        self.total_draws = matrix.shape[0]
        self._save()

    def _save(self):
        if not os.path.exists(DISTANCE_DIR):
            os.makedirs(DISTANCE_DIR)
        # save per-number occurrence indices
        with open(os.path.join(DISTANCE_DIR, "occurrence.tsv"), "w") as f:
            f.write("# For each number (1-49), the draw indices where it was drawn\n")
            f.write("# Used to compute gaps (draws since last appearance) for candidate combinations\n")
            f.write("number\tdraw_indices\n")
            for num in sorted(self.occurrence):
                f.write(str(num) + "\t" + "\t".join(str(i) for i in self.occurrence[num]) + "\n")
        # save recency score frequencies
        with open(os.path.join(DISTANCE_DIR, "frequency.tsv"), "w") as f:
            f.write("# Recency score = sum of gaps for all 6 numbers in a draw (sorted by count descending)\n")
            f.write("# Low score = all numbers appeared recently, high score = numbers haven't appeared in a while\n")
            f.write("recency_score\tcount\tprobability\n")
            for key, val in self.distance.items():
                f.write(str(key) + "\t" + str(val[0]) + "\t" + str(val[1]) + "\n")
        # save metadata
        with open(os.path.join(DISTANCE_DIR, "meta.tsv"), "w") as f:
            f.write("# Metadata for distance calculations\n")
            f.write("key\tvalue\n")
            f.write("total_draws\t" + str(self.total_draws) + "\n")
        # save per-draw recency scores
        with open(os.path.join(DISTANCE_DIR, "scores.tsv"), "w") as f:
            f.write("# Per-draw recency score (sum of gaps for all 6 numbers)\n")
            f.write("# score is empty for early draws where not all numbers have been seen yet\n")
            f.write("date\tscore\n")
            for date, score in self.draw_scores:
                f.write(str(date) + "\t" + (str(score) if score is not None else "") + "\n")

    @classmethod
    def load(cls):
        """Load pre-computed data from collect/distance/."""
        obj = cls.__new__(cls)
        obj.occurrence = {}
        with open(os.path.join(DISTANCE_DIR, "occurrence.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("number"):
                    continue
                cells = line.split("\t")
                num = int(cells[0])
                obj.occurrence[num] = [int(c) for c in cells[1:]]
        obj.total_draws = 0
        with open(os.path.join(DISTANCE_DIR, "meta.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("key"):
                    continue
                cells = line.split("\t")
                if cells[0] == "total_draws":
                    obj.total_draws = int(cells[1])
        obj.distance = OrderedDict()
        with open(os.path.join(DISTANCE_DIR, "frequency.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("recency"):
                    continue
                cells = line.split("\t")
                obj.distance[int(cells[0])] = [int(cells[1]), float(cells[2])]
        return obj
