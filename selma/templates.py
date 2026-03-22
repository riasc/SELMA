import os
from collections import OrderedDict

from selma.config import COLLECT_DIR

TEMPLATES_DIR = os.path.join(COLLECT_DIR, "templates")


class Templates:
    def getTemplateGroup(self, number):
        if number <= 9:
            group = 0
        elif number <= 19:
            group = 1
        elif number <= 29:
            group = 2
        elif number <= 39:
            group = 3
        elif number <= 49:
            group = 4
        return group

    def getStartTemplate(self, numbers):
        start = 0
        count = 0
        template = []

        for idx, val in enumerate(numbers):
            if idx < 6:
                group = self.getTemplateGroup(val)
                template.append(group)
                if idx == 0:
                    start = group
                    count = 1
                else:
                    if group == start:
                        count += 1

        return ((start, count), template)

    def __init__(self, matrix, data, from_date=None):
        """Collect occurrences and compute frequencies, save to collect/templates/."""
        print("\tcollect Templates")

        # collect occurrences from all data
        self.occ = []
        for x in range(0, matrix.shape[0]):
            (startCount, template) = self.getStartTemplate(matrix[x])
            self.occ.append((data[x], startCount, tuple(template)))

        # compute frequencies for the selected range
        filtered = self.occ
        if from_date:
            filtered = [(d, s, t) for d, s, t in self.occ if d >= from_date]

        tdraws = len(filtered)
        starts = {}
        templates = {}

        for date, startCount, template in filtered:
            if startCount not in starts:
                starts[startCount] = 1
            else:
                starts[startCount] += 1
            if template not in templates:
                templates[template] = 1
            else:
                templates[template] += 1

        starts = OrderedDict(sorted(starts.items(), key=lambda x: x[1], reverse=True))
        templates = OrderedDict(sorted(templates.items(), key=lambda x: x[1], reverse=True))

        for key in starts:
            starts[key] = [starts[key], starts[key] / tdraws]
        for key in templates:
            templates[key] = [templates[key], templates[key] / tdraws]

        self.starts = starts
        self.templates = templates
        self._save()

    def _save(self):
        if not os.path.exists(TEMPLATES_DIR):
            os.makedirs(TEMPLATES_DIR)
        # save occurrences
        with open(os.path.join(TEMPLATES_DIR, "occurrence.tsv"), "w") as f:
            f.write("# Per-draw template pattern: each number mapped to a group (0=1-9, 1=10-19, 2=20-29, 3=30-39, 4=40-49)\n")
            f.write("# start_group: group of the first number, streak: how many consecutive numbers share that group\n")
            f.write("date\tstart_group\tstreak\tg1\tg2\tg3\tg4\tg5\tg6\n")
            for x in self.occ:
                f.write(str(x[0]) + "\t" + str(x[1][0]) + "\t" + str(x[1][1]) + "\t")
                f.write("\t".join(str(g) for g in x[2]) + "\n")
        # save start frequencies
        with open(os.path.join(TEMPLATES_DIR, "frequency_starts.tsv"), "w") as f:
            f.write("# How often each starting group/streak combination occurred (sorted by count descending)\n")
            f.write("# group: decade group of first number, streak: consecutive count in same group\n")
            f.write("group\tstreak\tcount\tprobability\n")
            for key, val in self.starts.items():
                f.write(str(key[0]) + "\t" + str(key[1]) + "\t" + str(val[0]) + "\t" + str(val[1]) + "\n")
        # save template pattern frequencies
        with open(os.path.join(TEMPLATES_DIR, "frequency_patterns.tsv"), "w") as f:
            f.write("# How often each 6-group pattern occurred (sorted by count descending)\n")
            f.write("# g1-g6: decade group (0-4) for each of the 6 drawn numbers in ascending order\n")
            f.write("g1\tg2\tg3\tg4\tg5\tg6\tcount\tprobability\n")
            for key, val in self.templates.items():
                f.write("\t".join(str(g) for g in key) + "\t" + str(val[0]) + "\t" + str(val[1]) + "\n")

    @classmethod
    def load(cls):
        """Load pre-computed frequencies from collect/templates/."""
        obj = cls.__new__(cls)
        obj.occ = []
        obj.starts = OrderedDict()
        obj.templates = OrderedDict()
        with open(os.path.join(TEMPLATES_DIR, "frequency_starts.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("group"):
                    continue
                cells = line.split("\t")
                key = (int(cells[0]), int(cells[1]))
                obj.starts[key] = [int(cells[2]), float(cells[3])]
        with open(os.path.join(TEMPLATES_DIR, "frequency_patterns.tsv"), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("g1"):
                    continue
                cells = line.split("\t")
                key = tuple(int(c) for c in cells[0:6])
                obj.templates[key] = [int(cells[6]), float(cells[7])]
        return obj
