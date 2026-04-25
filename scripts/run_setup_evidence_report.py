from __future__ import annotations

from pathlib import Path

import pandas as pd

from v40.evidence_scoring import build_setup_comparison_table


def main() -> None:
    candidates = [Path('data/dataset_v40_research_full.csv'), Path('data/dataset_v40.csv')]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        print('missing_dataset')
        return

    df = pd.read_csv(path)
    table = build_setup_comparison_table(df)
    if table.empty:
        print('setup_evidence=EMPTY')
        return

    out = Path('data/setup_evidence_report.csv')
    table.to_csv(out, index=False)
    print(f'saved={out}')
    print('\n=== SETUP EVIDENCE REPORT ===')
    print(table.to_string(index=False))


if __name__ == '__main__':
    main()
