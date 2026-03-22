import os
from collections import OrderedDict

from selma.config import COLLECT_DIR

CONSECUTIVE_DIR = os.path.join(COLLECT_DIR, "consecutive")


class Consecutive:
    @staticmethod
    def find_pairs(numbers):
        """Find consecutive pairs in a sorted list of 6 numbers. Returns (count, list of pairs)."""
        nums = sorted(int(n) for n in numbers[:6])
        pairs = []
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                pairs.append((nums[i], nums[i + 1]))
        return len(pairs), pairs

    @staticmethod
    def count_pairs(numbers):
        """Count consecutive pairs (for use in prediction scoring)."""
        count, _ = Consecutive.find_pairs(numbers)
        return count

    def __init__(self, matrix, data, from_date=None):
        """Collect consecutive pair counts and compute frequencies."""
        print("\tcollect Consecutive")

        # collect occurrences from all data
        self.occ = []
        for x in range(0, matrix.shape[0]):
            count, pairs = self.find_pairs(matrix[x])
            self.occ.append((data[x], count, pairs))

        # compute frequencies for the selected range
        filtered = self.occ
        if from_date:
            filtered = [(d, c, p) for d, c, p in self.occ if d >= from_date]

        tdraws = len(filtered)
        pairDict = {}
        for date, count, pairs in filtered:
            if count in pairDict:
                pairDict[count] += 1
            else:
                pairDict[count] = 1

        pairDict = OrderedDict(sorted(pairDict.items(), key=lambda x: x[1], reverse=True))
        for key in pairDict:
            pairDict[key] = [pairDict[key], pairDict[key] / tdraws]

        self.freq = pairDict
        self._save()

    def _save(self):
        if not os.path.exists(CONSECUTIVE_DIR):
            os.makedirs(CONSECUTIVE_DIR)
        # save occurrences
        with open(os.path.join(CONSECUTIVE_DIR, "occurrence.tsv"), "w") as f:
            f.write("# Per-draw consecutive pairs (e.g. 12-13, 25-26)\n")
            f.write("# pairs_count: number of consecutive pairs, pairs: the actual pairs found\n")
            f.write("date\tpairs_count\tpairs\n")
            for date, count, pairs in self.occ:
                pairs_str = ",".join(str(a) + "-" + str(b) for a, b in pairs) if pairs else ""
                f.write(str(date) + "\t" + str(count) + "\t" + pairs_str + "\n")
        # save frequencies
        with open(os.path.join(CONSECUTIVE_DIR, "frequency.tsv"), "w") as f:
            f.write("# How often each consecutive pair count occurred (sorted by count descending)\n")
            f.write("# pairs_count: number of consecutive pairs in a draw (0-5)\n")
            f.write("pairs_count\tcount\tprobability\n")
            for key, val in self.freq.items():
                f.write(str(key) + "\t" + str(val[0]) + "\t" + str(val[1]) + "\n")

    @classmethod
    def load(cls):
        """Load pre-computed data from collect/consecutive/."""
        obj = cls.__new__(cls)
        obj.occ = []
        obj.freq = OrderedDict()
        with open(os.path.join(CONSECUTIVE_DIR, "frequency.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("pairs_count"):
                    continue
                cells = line.split("\t")
                obj.freq[int(cells[0])] = [int(cells[1]), float(cells[2])]
        return obj
