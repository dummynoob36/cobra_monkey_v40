from __future__ import annotations

import pandas as pd

from v40.simple_backtest import backtest_bank


def main() -> None:
    df = pd.read_csv('data/dataset_v40_research_full.csv')
    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')

    focus = ['A_REV_US', 'A_REV_GLOBAL', 'D_EU_TACTICAL', 'E_MOMO_UP', 'ABD_DELAYED_SWING']
    trades, summary = backtest_bank(df, setup_codes=focus, initial_bank=1000.0)

    print('trades_evaluated=', len(trades))
    print('\n=== BANK BACKTEST (1000 EUR) ===')
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
