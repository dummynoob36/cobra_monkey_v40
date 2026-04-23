from __future__ import annotations

import pandas as pd

from v40.risk_backtest import backtest_fixed_risk


FOCUS = ['A_REV_US', 'A_REV_GLOBAL', 'D_EU_TACTICAL']
CONFIGS = [
    {
        'label': 'baseline_caps_8x10',
        'max_concurrent': 8,
        'cooldown': 10,
        'setup_caps': {'A_REV_US': 2, 'A_REV_GLOBAL': 4, 'D_EU_TACTICAL': 2},
    },
    {
        'label': 'tight_caps_7x10',
        'max_concurrent': 7,
        'cooldown': 10,
        'setup_caps': {'A_REV_US': 2, 'A_REV_GLOBAL': 3, 'D_EU_TACTICAL': 2},
    },
    {
        'label': 'loose_caps_9x10',
        'max_concurrent': 9,
        'cooldown': 10,
        'setup_caps': {'A_REV_US': 2, 'A_REV_GLOBAL': 5, 'D_EU_TACTICAL': 2},
    },
    {
        'label': 'no_caps_8x10',
        'max_concurrent': 8,
        'cooldown': 10,
        'setup_caps': {},
    },
]


def main() -> None:
    df = pd.read_csv('data/dataset_v40_research_full.csv')
    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')

    rows = []
    for cfg in CONFIGS:
        trades, summary = backtest_fixed_risk(
            df,
            setup_codes=FOCUS,
            initial_bank=1000.0,
            risk_fraction=0.01,
            max_concurrent_positions=cfg['max_concurrent'],
            cooldown_days=cfg['cooldown'],
            setup_caps=cfg['setup_caps'],
        )
        if summary.empty:
            continue
        for _, row in summary.iterrows():
            rows.append({
                'config': cfg['label'],
                'setup_code': row['setup_code'],
                'trades': int(row['trades']),
                'final_bank': float(row['final_bank']),
                'max_drawdown_pct': float(row['max_drawdown_pct']),
                'avg_days_held': float(row['avg_days_held']),
                'avg_concurrent_exposure': float(row['avg_concurrent_exposure']),
                'avg_setup_exposure': float(row['avg_setup_exposure']),
                'expiry_rate_pct': float(row['expiry_rate_pct']),
            })

    out = pd.DataFrame(rows)
    if out.empty:
        print('EMPTY')
        return

    print(out.sort_values(['setup_code', 'config']).to_string(index=False))


if __name__ == '__main__':
    main()
