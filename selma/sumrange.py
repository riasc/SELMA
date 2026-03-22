import os
from collections import OrderedDict

from selma.config import COLLECT_DIR

SUMRANGE_DIR = os.path.join(COLLECT_DIR, "sumrange")


class SumRange:
    def __init__(self, matrix, data, from_date=None):
        """Collect sum occurrences and compute frequencies, save to collect/sumrange/."""
        print("\tcollect SumRange")

        # collect sum for each draw from all data
        self.occ = []
        for x in range(0, matrix.shape[0]):
            s = int(sum(matrix[x][:6]))
            self.occ.append((data[x], s))

        # compute frequencies for the selected range
        filtered = self.occ
        if from_date:
            filtered = [(d, s) for d, s in self.occ if d >= from_date]

        tdraws = len(filtered)
        sumDict = {}
        for date, s in filtered:
            if s in sumDict:
                sumDict[s] += 1
            else:
                sumDict[s] = 1

        sumDict = OrderedDict(sorted(sumDict.items(), key=lambda x: x[1], reverse=True))
        for key in sumDict:
            sumDict[key] = [sumDict[key], sumDict[key] / tdraws]

        self.freq = sumDict
        self._save()

    def _save(self):
        if not os.path.exists(SUMRANGE_DIR):
            os.makedirs(SUMRANGE_DIR)
        # save occurrences
        with open(os.path.join(SUMRANGE_DIR, "occurrence.tsv"), "w") as f:
            f.write("# Sum of the 6 main numbers per draw (theoretical range: 21-279, typical: ~100-200)\n")
            f.write("date\tsum\n")
            for date, s in self.occ:
                f.write(str(date) + "\t" + str(s) + "\n")
        # save frequencies
        with open(os.path.join(SUMRANGE_DIR, "frequency.tsv"), "w") as f:
            f.write("# How often each sum value occurred (sorted by count descending)\n")
            f.write("# Combinations with sums near the peak (~150) are historically most common\n")
            f.write("sum\tcount\tprobability\n")
            for key, val in self.freq.items():
                f.write(str(key) + "\t" + str(val[0]) + "\t" + str(val[1]) + "\n")

    @classmethod
    def load(cls):
        """Load pre-computed data from collect/sumrange/."""
        obj = cls.__new__(cls)
        obj.occ = []
        obj.freq = OrderedDict()
        with open(os.path.join(SUMRANGE_DIR, "frequency.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("sum"):
                    continue
                cells = line.split("\t")
                obj.freq[int(cells[0])] = [int(cells[1]), float(cells[2])]
        return obj
