from pathlib import Path
import numpy as np

from selma.archive import load_records


class Numbers:
    def __init__(self, path):
        self.path = Path(path)
        self.numbers = [str(p) for p in sorted(self.path.glob('*.txt'))]
        self.parseNumbers()

    def parseNumbers(self):
        records = load_records(self.path)
        self.datum = [day for day, _, _ in records]
        self.matrix = np.array([list(numbers) + [sz] for _, numbers, sz in records],
                               dtype=int).reshape((-1, 7))
