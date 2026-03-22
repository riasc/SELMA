import os
import random
import pickle
import numpy as np

from selma.config import BASE_DIR, NUMBERS_DIR, RESULTS_DIR
from selma.data import Numbers
from selma.oddeven import OddEven
from selma.templates import Templates
from selma.distance import DrawDistance
from selma.sumrange import SumRange
from selma.consecutive import Consecutive

MODEL_FILE = os.path.join(RESULTS_DIR, "model.pkl")
BACKTEST_MODEL_FILE = os.path.join(RESULTS_DIR, "backtest_model.tsv")
FEATURE_NAMES = ["oddeven", "start", "template", "sum", "consec", "recency"]


def _load_stats():
    """Load all pre-computed stats and normalization maxes."""
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


def compute_features(numbers, ode, tmpls, dist, sr, con, maxes):
    """Compute normalized feature vector for a combination. Returns list of 6 floats or None."""
    numbers = [int(n) for n in numbers]

    odeKey = ode.detOddEvenRatio(numbers)
    if odeKey not in ode.freq:
        return None
    n_oe = ode.freq[odeKey][1] / maxes["oddeven"]

    comboSum = sum(numbers)
    n_sum = sr.freq[comboSum][1] / maxes["sum"] if comboSum in sr.freq else 0.0

    consecPairs = Consecutive.count_pairs(numbers)
    n_con = con.freq[consecPairs][1] / maxes["consec"] if consecPairs in con.freq else 0.0

    (startKey, templateKey) = tmpls.getStartTemplate(numbers)
    n_start = tmpls.starts[startKey][1] / maxes["start"] if startKey in tmpls.starts else 0.0
    n_tmpl = tmpls.templates[tuple(templateKey)][1] / maxes["template"] if tuple(templateKey) in tmpls.templates else 0.0

    sumdrawdist = sum(dist.total_draws - dist.occurrence[v][-1] for v in numbers)
    n_rec = (dist.distance[sumdrawdist][1] / maxes["dist"]) if sumdrawdist in dist.distance else 0.0

    return [n_oe, n_start, n_tmpl, n_sum, n_con, n_rec]


def _generate_negative_samples(n_samples, ode, tmpls, dist, sr, con, maxes):
    """Generate random combinations as negative samples."""
    features = []
    count = 0
    while count < n_samples:
        combo = sorted(random.sample(range(1, 50), 6))
        feat = compute_features(combo, ode, tmpls, dist, sr, con, maxes)
        if feat is not None:
            features.append(feat)
            count += 1
    return features


def train(test_from="2026-01-01", neg_ratio=10):
    """Train logistic regression on historical draws vs random combinations."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler

    print("##### Train Model #####")

    ode, tmpls, dist, sr, con, tdraws, maxes = _load_stats()

    # positive samples: actual draws (excluding test period)
    nrs = Numbers(NUMBERS_DIR)
    pos_features = []
    for i, date in enumerate(nrs.datum):
        if test_from and date >= test_from:
            continue
        numbers = sorted([int(nrs.matrix[i][j]) for j in range(6)])
        feat = compute_features(numbers, ode, tmpls, dist, sr, con, maxes)
        if feat is not None:
            pos_features.append(feat)

    n_pos = len(pos_features)
    n_neg = n_pos * neg_ratio
    print(f"Positive samples (actual draws): {n_pos}")
    print(f"Negative samples (random combos): {n_neg}")

    # negative samples
    print("Generating negative samples...")
    neg_features = _generate_negative_samples(n_neg, ode, tmpls, dist, sr, con, maxes)

    # build dataset
    X = np.array(pos_features + neg_features)
    y = np.array([1] * n_pos + [0] * n_neg)

    # shuffle
    idx = np.random.permutation(len(X))
    X = X[idx]
    y = y[idx]

    print(f"Total samples: {len(X)}")
    print(f"Features: {FEATURE_NAMES}\n")

    # scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # cross-validate
    model = LogisticRegression(max_iter=1000, random_state=42)

    print("Cross-validation (5-fold)...")
    cv_auc = cross_val_score(model, X_scaled, y, cv=5, scoring="roc_auc")
    cv_acc = cross_val_score(model, X_scaled, y, cv=5, scoring="accuracy")
    print(f"AUC:      {cv_auc.mean():.4f} (+/- {cv_auc.std():.4f})")
    print(f"Accuracy: {cv_acc.mean():.4f} (+/- {cv_acc.std():.4f})")

    # train final model
    print("\nTraining final model...")
    model.fit(X_scaled, y)

    # coefficients (learned weights)
    print("\nLearned coefficients:")
    coefs = model.coef_[0]
    for name, coef in sorted(zip(FEATURE_NAMES, coefs), key=lambda x: abs(x[1]), reverse=True):
        print(f"  {name:<12} {coef:+.4f}")
    print(f"  {'intercept':<12} {model.intercept_[0]:+.4f}")

    # save model + scaler
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    with open(MODEL_FILE, "wb") as f:
        pickle.dump({"model": model, "scaler": scaler, "maxes": maxes}, f)
    print(f"\nModel saved to {MODEL_FILE}")

    # save coefficients
    coefs_file = os.path.join(RESULTS_DIR, "model_coefficients.tsv")
    with open(coefs_file, "w") as f:
        f.write("# Logistic regression coefficients (learned feature weights)\n")
        f.write(f"# Positive samples: {n_pos}, Negative samples: {n_neg}\n")
        f.write(f"# AUC: {cv_auc.mean():.4f} (+/- {cv_auc.std():.4f})\n")
        f.write(f"# Accuracy: {cv_acc.mean():.4f} (+/- {cv_acc.std():.4f})\n")
        f.write("feature\tcoefficient\n")
        for name, coef in zip(FEATURE_NAMES, coefs):
            f.write(f"{name}\t{coef:+.4f}\n")
        f.write(f"intercept\t{model.intercept_[0]:+.4f}\n")
    print(f"Coefficients saved to {coefs_file}")

    return model, scaler


def load_model():
    """Load trained model and scaler."""
    with open(MODEL_FILE, "rb") as f:
        saved = pickle.load(f)
    return saved["model"], saved["scaler"], saved["maxes"]


def backtest_model(test_from="2026-01-01"):
    """Score actual draws using the trained model."""
    print("##### Model Backtest #####")

    ode, tmpls, dist, sr, con, tdraws, maxes = _load_stats()
    model, scaler, _ = load_model()
    print("Model loaded from " + MODEL_FILE)

    # load test draws
    nrs = Numbers(NUMBERS_DIR)
    test_draws = []
    for i, date in enumerate(nrs.datum):
        if date >= test_from:
            numbers = sorted([int(nrs.matrix[i][j]) for j in range(6)])
            test_draws.append((date, numbers))

    if not test_draws:
        print("No draws found from " + test_from)
        return

    print(f"\n{'Date':<14} {'Numbers':<30} {'Prob':>8} {'OE':>6} {'St':>6} {'Tp':>6} {'Sum':>6} {'Con':>6} {'Rec':>6}")
    print("-" * 100)

    scores = []
    results = []
    for date, numbers in test_draws:
        feat = compute_features(numbers, ode, tmpls, dist, sr, con, maxes)
        if feat is not None:
            feat_scaled = scaler.transform(np.array([feat]))
            prob = model.predict_proba(feat_scaled)[0][1]
            scores.append(prob)
            results.append((date, numbers, feat, prob))
            print(f"{date:<14} {','.join(str(n) for n in numbers):<30} {prob:>8.4f} "
                  f"{feat[0]:>6.3f} {feat[1]:>6.3f} {feat[2]:>6.3f} "
                  f"{feat[3]:>6.3f} {feat[4]:>6.3f} {feat[5]:>6.3f}")
        else:
            scores.append(0.0)
            results.append((date, numbers, None, 0.0))
            print(f"{date:<14} {','.join(str(n) for n in numbers):<30} {'FILTERED':>8}")

    print("-" * 100)
    avg = sum(scores) / len(scores)
    max_s = max(scores)
    min_s = min(scores)
    filtered = scores.count(0.0)
    print(f"\nDraws: {len(scores)}, Filtered: {filtered}")
    print(f"Probability — avg: {avg:.4f}, min: {min_s:.4f}, max: {max_s:.4f}")

    # save results
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    with open(BACKTEST_MODEL_FILE, "w") as f:
        f.write("# Model backtest: logistic regression probability for actual draws\n")
        f.write("date\tn1\tn2\tn3\tn4\tn5\tn6\toddeven\tstart\ttemplate\tsum\tconsec\trecency\tprobability\n")
        for date, numbers, feat, prob in results:
            f.write(date + "\t" + "\t".join(str(n) for n in numbers) + "\t")
            if feat is not None:
                f.write("\t".join(f"{v:.4f}" for v in feat) + "\t")
                f.write(f"{prob:.6f}\n")
            else:
                f.write("\t\t\t\t\t\t0.000000\n")
    print("Saved to " + BACKTEST_MODEL_FILE)
