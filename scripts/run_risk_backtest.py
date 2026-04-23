from __future__ import annotations

import argparse

import pandas as pd

from v40.operability import DEFAULT_SETUP_CAPS
from v40.risk_backtest import backtest_fixed_risk, summarize_trade_lifecycle


VALID_FOCUS = ['A_REV_US', 'A_REV_GLOBAL', 'D_EU_TACTICAL']


def main() -> None:
    parser = argparse.ArgumentParser(description='Run fixed-risk backtest with operability constraints.')
    parser.add_argument('--max-concurrent', type=int, default=None, help='Maximum simultaneous open positions.')
    parser.add_argument('--cooldown-days', type=int, default=0, help='Cooldown after exit before re-entering same ticker.')
    parser.add_argument('--risk-fraction', type=float, default=0.01, help='Risk per trade as bank fraction.')
    parser.add_argument('--initial-bank', type=float, default=1000.0, help='Initial capital.')
    args = parser.parse_args()

    df = pd.read_csv('data/dataset_v40_research_full.csv')
    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')

    trades, summary = backtest_fixed_risk(
        df,
        setup_codes=VALID_FOCUS,
        initial_bank=args.initial_bank,
        risk_fraction=args.risk_fraction,
        max_concurrent_positions=args.max_concurrent,
        cooldown_days=args.cooldown_days,
        setup_caps=DEFAULT_SETUP_CAPS,
    )

    print('trades_evaluated=', len(trades))
    print('\n=== FIXED RISK BACKTEST (OPERABILITY-AWARE) ===')
    print(summary.to_string(index=False))

    lifecycle = summarize_trade_lifecycle(trades)
    if not lifecycle.empty:
        print('\n=== TRADE LIFECYCLE SUMMARY ===')
        print(lifecycle.to_string(index=False))


if __name__ == '__main__':
    main()
