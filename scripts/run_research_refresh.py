from __future__ import annotations

import pandas as pd

from v40.engine.build_dataset_v40 import build_dataset_v40
from v40.pattern_validation import summarize_pattern_validation


def main() -> None:
    df, start_date = build_dataset_v40()
    print(f"dataset_rows={len(df)} start_date={start_date}")

    summary = summarize_pattern_validation(df)
    if summary.empty:
        print("validation_summary=EMPTY")
        return

    print("\n=== VALIDATION SUMMARY ===")
    print(summary.to_string(index=False))

    min_signals = 20
    filt = summary[summary["signals"] >= min_signals].copy()
    if not filt.empty:
        print(f"\n=== TOP AVG5 (min {min_signals}) ===")
        print(filt.sort_values("avg_return_5d", ascending=False).to_string(index=False))
        print(f"\n=== TOP AVG20 (min {min_signals}) ===")
        print(filt.sort_values("avg_return_20d", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
