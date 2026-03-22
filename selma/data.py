import os
import numpy as np

from selma.config import NUMBERS_DIR


class Numbers:
    numbers = [] # files that contain the numbers
    matrix = np.empty((0,7))
    datum = []

    def __init__(self, path):
        # scan folder for files
        for root,dirs,files in os.walk(NUMBERS_DIR):
            for name in sorted(files):
                self.numbers.append(os.path.join(root,name))
        self.parseNumbers()

    def parseNumbers(self):
        for filename in self.numbers:
            with open(filename) as f:
                next(f) # exclude header
                for line in f:
                    cells = line.split("\t")
                    self.datum.append(cells[0]) # date
                    nrs = cells[1:8] # numbers
                    self.matrix = np.append(self.matrix,[nrs],axis=0).astype(int)
            f.close()
