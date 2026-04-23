from __future__ import annotations

import pandas as pd


def main() -> None:
    df = pd.read_csv('data/dataset_v40_research_full.csv')
    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')
    df = df[df['setup_code'].isin(['A_REV_US', 'A_REV_GLOBAL', 'D_EU_TACTICAL'])].copy()

    if df.empty:
        print('no_signals')
        return

    print('\n=== SIGNAL LOAD BY SETUP ===')
    grouped = df.groupby('setup_code').agg(
        total_signals=('ticker', 'count'),
        unique_tickers=('ticker', 'nunique'),
        avg_holding_days=('holding_horizon_days', 'mean'),
    ).reset_index()
    print(grouped.to_string(index=False))

    print('\n=== DAILY SIGNAL STATS ===')
    per_day = df.groupby(['setup_code', df['signal_date'].dt.date]).size().reset_index(name='n_signals')
    daily_stats = per_day.groupby('setup_code').agg(
        active_days=('n_signals', 'count'),
        avg_signals_per_day=('n_signals', 'mean'),
        median_signals_per_day=('n_signals', 'median'),
        p90_signals_per_day=('n_signals', lambda s: s.quantile(0.9)),
        max_signals_day=('n_signals', 'max'),
    ).reset_index()
    print(daily_stats.to_string(index=False))

    print('\n=== COMBINED DAILY LOAD ===')
    combined = df.groupby(df['signal_date'].dt.date).size()
    print({
        'days': int(combined.shape[0]),
        'avg_signals_per_day': round(float(combined.mean()), 2),
        'median_signals_per_day': round(float(combined.median()), 2),
        'p90_signals_per_day': round(float(combined.quantile(0.9)), 2),
        'max_signals_day': int(combined.max()),
    })


if __name__ == '__main__':
    main()
