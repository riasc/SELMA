import os

# project root directory (one level up from this file)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUMBERS_DIR = os.path.join(BASE_DIR, "numbers")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
COLLECT_DIR = os.path.join(BASE_DIR, "collect")
