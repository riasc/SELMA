import sys
from selma.prediction import collect, predict, backtest, optimize_weights
from selma.model import train, backtest_model
from selma.visualize import generate_html

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "predict"

    if command == "collect":
        from_date = "2000-01-01"
        to_date = None
        if len(sys.argv) > 2:
            from_date = sys.argv[2]
        if len(sys.argv) > 3:
            to_date = sys.argv[3]
        collect(from_date=from_date, to_date=to_date)
    elif command == "predict":
        predict()
    elif command == "backtest":
        test_from = "2026-01-01"
        if len(sys.argv) > 2:
            test_from = sys.argv[2]
        backtest(test_from=test_from)
    elif command == "optimize":
        test_from = "2026-01-01"
        if len(sys.argv) > 2:
            test_from = sys.argv[2]
        optimize_weights(test_from=test_from)
    elif command == "train":
        test_from = "2026-01-01"
        if len(sys.argv) > 2:
            test_from = sys.argv[2]
        train(test_from=test_from)
    elif command == "backtest-model":
        test_from = "2026-01-01"
        if len(sys.argv) > 2:
            test_from = sys.argv[2]
        backtest_model(test_from=test_from)
    elif command == "visualize":
        generate_html()
    else:
        print(f"Unknown command: {command}")
        print("Usage:")
        print("  python -m selma collect [FROM TO]       # compute & save stats")
        print("  python -m selma backtest [FROM]          # score actual draws (weighted sum)")
        print("  python -m selma optimize [FROM]          # find optimal weights")
        print("  python -m selma train [FROM]             # train logistic regression model")
        print("  python -m selma backtest-model [FROM]    # score actual draws (model)")
        print("  python -m selma predict                  # score all combinations")
        print("  python -m selma visualize                # generate HTML dashboard")
        sys.exit(1)
