import os
import itertools
import time

from selma.config import BASE_DIR, NUMBERS_DIR, RESULTS_DIR
from selma.data import Numbers
from selma.oddeven import OddEven
from selma.templates import Templates
from selma.distance import DrawDistance
from selma.sumrange import SumRange
from selma.consecutive import Consecutive
from selma.hotcold import HotCold
from selma.profiles import Profiles

WEIGHTS_FILE = os.path.join(RESULTS_DIR, "weights.tsv")
BACKTEST_FILE = os.path.join(RESULTS_DIR, "backtest.tsv")
PREDICTION_FILE = os.path.join(RESULTS_DIR, "predictions_unsorted.tsv")
PREDICTION_SORTED_FILE = os.path.join(RESULTS_DIR, "numbers.txt")

DEFAULT_WEIGHTS = [0.20, 0.10, 0.15, 0.20, 0.20, 0.15]
WEIGHT_LABELS = ["oddeven", "start", "template", "sum", "consec", "recency"]


def _ensure_results_dir():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)


def _load_weights():
    """Load weights from results/weights.tsv if it exists, otherwise use defaults."""
    if os.path.exists(WEIGHTS_FILE):
        weights = []
        with open(WEIGHTS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("feature"):
                    continue
                cells = line.split("\t")
                weights.append(float(cells[1]))
        if len(weights) == 6:
            print("Loaded weights from " + WEIGHTS_FILE)
            return weights
    print("Using default weights")
    return list(DEFAULT_WEIGHTS)


def _save_weights(weights):
    """Save weights to results/weights.tsv."""
    _ensure_results_dir()
    with open(WEIGHTS_FILE, "w") as f:
        f.write("# Optimal weights found by optimization\n")
        f.write("feature\tweight\n")
        for label, w in zip(WEIGHT_LABELS, weights):
            f.write(f"{label}\t{w:.2f}\n")
    print("Weights saved to " + WEIGHTS_FILE)


def _load_stats():
    """Load all pre-computed stats and return them with normalization maxes."""
    ode = OddEven.load()
    tmpls = Templates.load()
    dist = DrawDistance.load()
    sr = SumRange.load()
    con = Consecutive.load()

    tdraws = sum(val[0] for val in ode.freq.values())

    maxes = {
        "oddeven": max(v[1] for v in ode.freq.values()),
        "start": max(v[1] for v in tmpls.starts.values()),
        "template": max(v[1] for v in tmpls.templates.values()),
        "sum": max(v[1] for v in sr.freq.values()),
        "consec": max(v[1] for v in con.freq.values()),
        "dist": max(v[1] for v in dist.distance.values()) if dist.distance else 1.0,
    }

    return ode, tmpls, dist, sr, con, tdraws, maxes


def _precompute_draw_features(test_draws, ode, tmpls, dist, sr, con, tdraws, maxes):
    """Pre-compute normalized feature scores for all test draws."""
    results = []
    for date, numbers in test_draws:
        odeKey = ode.detOddEvenRatio(numbers)
        if odeKey not in ode.freq:
            results.append((date, numbers, None))
            continue

        comboSum = sum(numbers)
        if comboSum not in sr.freq:
            results.append((date, numbers, None))
            continue

        consecPairs = Consecutive.count_pairs(numbers)
        if consecPairs not in con.freq:
            results.append((date, numbers, None))
            continue

        (startKey, templateKey) = tmpls.getStartTemplate(numbers)
        if startKey not in tmpls.starts or tuple(templateKey) not in tmpls.templates:
            results.append((date, numbers, None))
            continue

        sumdrawdist = sum(dist.total_draws - dist.occurrence[v][-1] for v in numbers)
        drawdistProb = dist.distance[sumdrawdist][1] if sumdrawdist in dist.distance else 0.0

        features = [
            ode.freq[odeKey][1] / maxes["oddeven"],
            tmpls.starts[startKey][1] / maxes["start"],
            tmpls.templates[tuple(templateKey)][1] / maxes["template"],
            sr.freq[comboSum][1] / maxes["sum"],
            con.freq[consecPairs][1] / maxes["consec"],
            (drawdistProb / maxes["dist"]) if drawdistProb > 0 else 0.0,
        ]
        results.append((date, numbers, features))
    return results


def _score_with_weights(precomputed, weights):
    """Score pre-computed features with given weights. Returns average score."""
    total = 0.0
    count = 0
    for date, numbers, features in precomputed:
        if features is None:
            continue
        total += sum(w * f for w, f in zip(weights, features))
        count += 1
    return total / count if count > 0 else 0.0


def _generate_weight_combos(step=0.05):
    """Generate all weight combinations (6 weights, sum to 1.0, step size)."""
    steps = int(1.0 / step)
    combos = []

    def _recurse(remaining, depth, current):
        if depth == 5:
            current.append(remaining * step)
            combos.append(tuple(round(w, 2) for w in current))
            current.pop()
            return
        for i in range(remaining + 1):
            current.append(i * step)
            _recurse(remaining - i, depth + 1, current)
            current.pop()

    _recurse(steps, 0, [])
    return combos


def _load_test_draws(test_from):
    """Load actual draws from a given date onwards."""
    nrs = Numbers(NUMBERS_DIR)
    test_draws = []
    for i, date in enumerate(nrs.datum):
        if date >= test_from:
            numbers = sorted([int(nrs.matrix[i][j]) for j in range(6)])
            test_draws.append((date, numbers))
    return test_draws


# ==================== COMMANDS ====================


def collect(from_date="2000-01-01", to_date=None):
    """Collect occurrences and compute frequencies, save to collect/."""
    print("##### Collect #####")
    nrs = Numbers(NUMBERS_DIR)
    matrix = nrs.matrix
    data = nrs.datum

    if to_date:
        end = next((i for i, d in enumerate(data) if d > to_date), len(data))
        matrix = matrix[:end]
        data = data[:end]

    print("total draws: " + str(matrix.shape[0]))
    print("from " + str(data[0]) + " to " + str(data[-1]))
    print("frequency range: " + from_date + " onwards")

    OddEven(matrix, data, from_date=from_date)
    Templates(matrix, data, from_date=from_date)
    DrawDistance(matrix, data, from_date=from_date)
    SumRange(matrix, data, from_date=from_date)
    Consecutive(matrix, data, from_date=from_date)
    HotCold(matrix, data, from_date=from_date)
    Profiles(matrix, data, from_date=from_date)

    print("Saved to collect/")


def backtest(test_from="2026-01-01"):
    """Score actual draws against pre-computed stats."""
    print("##### Backtest #####")
    print("Scoring actual draws from " + test_from + "\n")

    ode, tmpls, dist, sr, con, tdraws, maxes = _load_stats()
    weights = _load_weights()
    print("Stats based on " + str(tdraws) + " draws")
    print("Weights: " + "  ".join(f"{l}={w:.2f}" for l, w in zip(WEIGHT_LABELS, weights)))
    print()

    test_draws = _load_test_draws(test_from)
    if not test_draws:
        print("No draws found from " + test_from)
        return

    precomputed = _precompute_draw_features(test_draws, ode, tmpls, dist, sr, con, tdraws, maxes)

    # print to console
    print(f"{'Date':<14} {'Numbers':<30} {'Score':>8} {'OE':>6} {'St':>6} {'Tp':>6} {'Sum':>6} {'Con':>6} {'Rec':>6}")
    print("-" * 100)

    scores = []
    for date, numbers, features in precomputed:
        nums_str = ",".join(str(n) for n in numbers)
        if features is not None:
            score = sum(w * f for w, f in zip(weights, features))
            scores.append(score)
            print(f"{date:<14} {nums_str:<30} {score:>8.4f} "
                  f"{features[0]:>6.3f} {features[1]:>6.3f} {features[2]:>6.3f} "
                  f"{features[3]:>6.3f} {features[4]:>6.3f} {features[5]:>6.3f}")
        else:
            scores.append(0.0)
            print(f"{date:<14} {nums_str:<30} {'FILTERED':>8}")

    print("-" * 100)
    avg = sum(scores) / len(scores)
    max_s = max(scores)
    min_s = min(scores)
    filtered = scores.count(0.0)
    print(f"\nDraws: {len(scores)}, Filtered: {filtered}")
    print(f"Scores — avg: {avg:.4f}, min: {min_s:.4f}, max: {max_s:.4f}")

    # save to file
    _ensure_results_dir()
    with open(BACKTEST_FILE, "w") as f:
        f.write("# Backtest results: actual draws scored against collected stats\n")
        f.write("# weights: " + "  ".join(f"{l}={w:.2f}" for l, w in zip(WEIGHT_LABELS, weights)) + "\n")
        f.write("date\tn1\tn2\tn3\tn4\tn5\tn6\toddeven\tstart\ttemplate\tsum\tconsec\trecency\ttotal\n")
        for (date, numbers, features), score in zip(precomputed, scores):
            f.write(date + "\t" + "\t".join(str(n) for n in numbers) + "\t")
            if features is not None:
                f.write("\t".join(f"{feat:.4f}" for feat in features) + "\t")
                f.write(f"{score:.6f}\n")
            else:
                f.write("\t\t\t\t\t\t0.000000\n")
    print("Saved to " + BACKTEST_FILE)


def optimize_weights(test_from="2026-01-01"):
    """Find optimal weights by grid search."""
    print("##### Optimize Weights #####")

    ode, tmpls, dist, sr, con, tdraws, maxes = _load_stats()

    test_draws = _load_test_draws(test_from)
    if not test_draws:
        print("No draws found from " + test_from)
        return

    print(f"Test draws: {len(test_draws)}")

    precomputed = _precompute_draw_features(test_draws, ode, tmpls, dist, sr, con, tdraws, maxes)
    scored_count = sum(1 for _, _, f in precomputed if f is not None)
    filtered_count = len(precomputed) - scored_count
    print(f"Scorable: {scored_count}, Filtered: {filtered_count}")

    print("Generating weight combinations (step=0.05)...")
    combos = _generate_weight_combos(step=0.05)
    print(f"Testing {len(combos)} weight combinations...\n")

    start_time = time.time()
    results = []
    for weights in combos:
        avg = _score_with_weights(precomputed, weights)
        results.append((avg, weights))

    results.sort(key=lambda x: x[0], reverse=True)
    elapsed = time.time() - start_time

    best_score, best_weights = results[0]

    print(f"Optimization done in {elapsed:.1f}s")
    print(f"\nBest average score: {best_score:.4f}")
    print(f"\nOptimal weights:")
    for label, w in zip(WEIGHT_LABELS, best_weights):
        print(f"  {label:<12} {w:.2f}")

    print(f"\nTop 10 weight combinations:")
    print(f"{'Score':>8}  {'OE':>5} {'St':>5} {'Tp':>5} {'Sum':>5} {'Con':>5} {'Rec':>5}")
    for avg, weights in results[:10]:
        print(f"{avg:>8.4f}  {weights[0]:>5.2f} {weights[1]:>5.2f} {weights[2]:>5.2f} "
              f"{weights[3]:>5.2f} {weights[4]:>5.2f} {weights[5]:>5.2f}")

    # save optimal weights
    _save_weights(best_weights)

    return best_weights


def predict(use_model=False):
    """Load pre-computed data, filter and score all combinations."""
    print("##### Lottery Prediction #####")

    ode, tmpls, dist, sr, con, tdraws, maxes = _load_stats()

    model = None
    scaler = None
    weights = None

    if use_model:
        from selma.model import load_model
        model, scaler, _ = load_model()
        print("Scoring with logistic regression model")
    else:
        weights = _load_weights()
        print("Scoring with weighted sum")
        print("Weights: " + "  ".join(f"{l}={w:.2f}" for l, w in zip(WEIGHT_LABELS, weights)))

    print("draws in frequency data: " + str(tdraws))

    # pre-compute valid values for early filtering
    valid_oddeven = set(ode.freq.keys())
    valid_sums = set(sr.freq.keys())
    valid_consec = set(con.freq.keys())

    _ensure_results_dir()
    hPrediction = open(PREDICTION_FILE, "w")

    # header
    hPrediction.write("n1\tn2\tn3\tn4\tn5\tn6\t")
    hPrediction.write("oddeven\tstart\ttemplate\trecency\tsum\tconsec\tscore\n")

    total_combos = 0
    scored_combos = 0
    skipped = 0
    start_time = time.time()

    import numpy as np

    for combo in itertools.combinations(range(1, 50), 6):
        total_combos += 1
        means = list(combo)

        # --- early filters ---
        odeKey = ode.detOddEvenRatio(means)
        if odeKey not in valid_oddeven:
            skipped += 1
            continue
        odeProb = ode.freq[odeKey][1]

        comboSum = sum(means)
        if comboSum not in valid_sums:
            skipped += 1
            continue
        sumProb = sr.freq[comboSum][1]

        consecPairs = Consecutive.count_pairs(means)
        if consecPairs not in valid_consec:
            skipped += 1
            continue
        consecProb = con.freq[consecPairs][1]

        (startKey, templateKey) = tmpls.getStartTemplate(means)
        if startKey not in tmpls.starts:
            skipped += 1
            continue
        startProb = tmpls.starts[startKey][1]
        if tuple(templateKey) not in tmpls.templates:
            skipped += 1
            continue
        templateProb = tmpls.templates[tuple(templateKey)][1]

        # recency (soft)
        sumdrawdist = sum(dist.total_draws - dist.occurrence[val][-1] for val in means)
        if sumdrawdist in dist.distance:
            drawdistProb = dist.distance[sumdrawdist][1]
        else:
            drawdistProb = 0.0

        # --- normalize ---
        features = [
            odeProb / maxes["oddeven"],
            startProb / maxes["start"],
            templateProb / maxes["template"],
            sumProb / maxes["sum"],
            consecProb / maxes["consec"],
            (drawdistProb / maxes["dist"]) if drawdistProb > 0 else 0.0,
        ]

        # --- score ---
        if use_model:
            feat_scaled = scaler.transform(np.array([features]))
            totalScore = model.predict_proba(feat_scaled)[0][1]
        else:
            totalScore = sum(w * f for w, f in zip(weights, features))

        for val in means:
            hPrediction.write(str(val) + "\t")
        hPrediction.write("\t".join(f"{f:.4f}" for f in features) + "\t")
        hPrediction.write(f"{totalScore:.6f}\n")

        scored_combos += 1

    hPrediction.close()

    elapsed = time.time() - start_time
    print(f"\nTotal combinations: {total_combos:,}")
    print(f"Skipped (zero probability): {skipped:,}")
    print(f"Scored: {scored_combos:,}")
    print(f"Time: {elapsed:.1f}s")

    # sort by score descending, remove unsorted file
    os.system("head -1 " + PREDICTION_FILE + " > " + PREDICTION_SORTED_FILE +
              " && tail -n +2 " + PREDICTION_FILE + " | sort -t '\t' -k 13,13rg >> " + PREDICTION_SORTED_FILE)
    os.remove(PREDICTION_FILE)

    print("Results saved to " + PREDICTION_SORTED_FILE)
