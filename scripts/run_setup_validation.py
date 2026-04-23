from __future__ import annotations

import pandas as pd

from v40.setup_validation import summarize_setup_validation


def main() -> None:
    df = pd.read_csv('data/dataset_v40.csv')
    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')

    summary = summarize_setup_validation(df)
    if summary.empty:
        print('setup_validation=EMPTY')
        return

    print('\n=== SETUP VALIDATION SUMMARY ===')
    print(summary.to_string(index=False))

    min_signals = 20
    filt = summary[summary['signals'] >= min_signals].copy()
    if not filt.empty:
        print(f'\n=== TOP SETUPS AVG5 (min {min_signals}) ===')
        print(filt.sort_values('avg_return_5d', ascending=False).to_string(index=False))
        print(f'\n=== TOP SETUPS AVG20 (min {min_signals}) ===')
        print(filt.sort_values('avg_return_20d', ascending=False).to_string(index=False))


if __name__ == '__main__':
    main()
