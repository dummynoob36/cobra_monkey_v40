import pandas as pd

from v40.pattern_quality import classify_signal_quality, annotate_signal_quality


def test_classify_signal_quality_prioritizes_a_us():
    tier, note = classify_signal_quality(pd.Series({
        'ticker': 'AAPL',
        'pattern_family': 'A',
        'trend_regime': 'DOWN',
    }))
    assert tier == 'HIGH'
    assert 'A en US' in note


def test_annotate_signal_quality_adds_columns():
    df = pd.DataFrame([
        {'ticker': 'AAPL', 'pattern_family': 'A', 'trend_regime': 'DOWN'},
        {'ticker': 'SAN.MC', 'pattern_family': 'D', 'trend_regime': 'RANGE'},
    ])
    out = annotate_signal_quality(df)
    assert 'quality_tier' in out.columns
    assert 'quality_note' in out.columns
    assert 'market_bucket' in out.columns
    assert out.loc[0, 'quality_tier'] == 'HIGH'
