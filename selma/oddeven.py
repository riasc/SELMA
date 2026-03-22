import os
from collections import OrderedDict

from selma.config import COLLECT_DIR

ODDEVEN_DIR = os.path.join(COLLECT_DIR, "oddeven")


class OddEven:
    def detOddEvenRatio(self, number):
        countsOdd = 0
        countsEven = 0
        for idx, val in enumerate(number):
            if idx < 6:
                if val % 2 == 0:
                    countsEven += 1
                else:
                    countsOdd += 1
        return (countsOdd, countsEven)

    def __init__(self, matrix, data, from_date=None):
        """Collect occurrences and compute frequencies, save to collect/oddeven/."""
        print("\tcollect OddEven")

        # collect occurrences from all data
        self.occ = []
        for x in range(0, matrix.shape[0]):
            ratio = self.detOddEvenRatio(matrix[x])
            self.occ.append((data[x], ratio))

        # compute frequencies for the selected range
        filtered = self.occ
        if from_date:
            filtered = [(d, r) for d, r in self.occ if d >= from_date]

        tdraws = len(filtered)
        oddEvenDict = {}
        for date, ratio in filtered:
            if ratio in oddEvenDict:
                oddEvenDict[ratio] += 1
            else:
                oddEvenDict[ratio] = 1

        oddEvenDict = OrderedDict(sorted(oddEvenDict.items(), key=lambda x: x[1], reverse=True))
        for key in oddEvenDict:
            oddEvenDict[key] = [oddEvenDict[key], oddEvenDict[key] / tdraws]

        self.freq = oddEvenDict
        self._save(tdraws)

    def _save(self, tdraws):
        if not os.path.exists(ODDEVEN_DIR):
            os.makedirs(ODDEVEN_DIR)
        # save occurrences
        with open(os.path.join(ODDEVEN_DIR, "occurrence.tsv"), "w") as f:
            f.write("# Per-draw odd/even ratio of the 6 main numbers\n")
            f.write("# odd: count of odd numbers, even: count of even numbers (always sum to 6)\n")
            f.write("date\todd\teven\n")
            for date, ratio in self.occ:
                f.write(str(date) + "\t" + str(ratio[0]) + "\t" + str(ratio[1]) + "\n")
        # save frequencies
        with open(os.path.join(ODDEVEN_DIR, "frequency.tsv"), "w") as f:
            f.write("# How often each odd/even ratio occurred across all draws (sorted by count descending)\n")
            f.write("# count: number of draws with this ratio, probability: count / total draws\n")
            f.write("odd\teven\tcount\tprobability\n")
            for key, val in self.freq.items():
                f.write(str(key[0]) + "\t" + str(key[1]) + "\t" + str(val[0]) + "\t" + str(val[1]) + "\n")

    @classmethod
    def load(cls):
        """Load pre-computed frequencies from collect/oddeven/."""
        obj = cls.__new__(cls)
        obj.occ = []
        obj.freq = OrderedDict()
        with open(os.path.join(ODDEVEN_DIR, "frequency.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("odd"):
                    continue
                cells = line.split("\t")
                key = (int(cells[0]), int(cells[1]))
                obj.freq[key] = [int(cells[2]), float(cells[3])]
        return obj
