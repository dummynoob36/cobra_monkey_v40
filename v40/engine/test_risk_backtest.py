from __future__ import annotations

import pandas as pd

from v40.risk_backtest import summarize_trade_lifecycle


def test_summarize_trade_lifecycle_basic_metrics():
    trades = pd.DataFrame([
        {
            'setup_code': 'A_REV_US',
            'r_multiple': 1.5,
            'return_pct': 0.03,
            'days_held': 4,
            'exit_reason': 'target',
            'concurrent_positions_at_entry': 0,
        },
        {
            'setup_code': 'A_REV_US',
            'r_multiple': -1.0,
            'return_pct': -0.02,
            'days_held': 3,
            'exit_reason': 'stop',
            'concurrent_positions_at_entry': 1,
        },
    ])

    summary = summarize_trade_lifecycle(trades)

    assert len(summary) == 1
    row = summary.iloc[0]
    assert row['setup_code'] == 'A_REV_US'
    assert row['trades'] == 2
    assert row['avg_days_held'] == 3.5
    assert row['avg_days_to_target'] == 4.0
    assert row['avg_days_to_stop'] == 3.0
    assert row['max_concurrent_exposure'] == 1
