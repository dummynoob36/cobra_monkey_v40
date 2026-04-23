import pandas as pd

from v40.pattern_validation import summarize_pattern_validation


def test_summarize_pattern_validation_aggregates_forward_returns():
    df = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "signal_date": pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-02"]),
            "pattern_family": ["A", "A", "B"],
            "ret_5d": [0.10, -0.05, 0.03],
            "ret_10d": [0.20, -0.10, 0.04],
            "ret_20d": [0.30, -0.20, 0.05],
        }
    )

    out = summarize_pattern_validation(df, forward_days=(5, 10, 20))

    row_a = out[out["pattern_family"] == "A"].iloc[0]
    row_b = out[out["pattern_family"] == "B"].iloc[0]

    assert row_a["signals"] == 2
    assert row_a["unique_tickers"] == 1
    assert row_a["hit_rate_5d"] == 50.0
    assert round(row_a["avg_return_5d"], 4) == 2.5
    assert round(row_a["median_return_5d"], 4) == 2.5

    assert row_b["signals"] == 1
    assert row_b["unique_tickers"] == 1
    assert row_b["hit_rate_5d"] == 100.0
    assert round(row_b["avg_return_10d"], 4) == 4.0
