from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd

from v40.walkforward_validation import run_walkforward_validation


def main() -> None:
    parser = argparse.ArgumentParser(description='Run simplified walk-forward validation.')
    parser.add_argument('--test-days', type=int, default=30)
    parser.add_argument('--step-days', type=int, default=30)
    parser.add_argument('--min-train-rows', type=int, default=400)
    parser.add_argument('--min-evidence-score', type=int, default=60)
    parser.add_argument('--max-folds', type=int, default=12)
    args = parser.parse_args()

    path = Path('data/dataset_v40_research_full.csv')
    if not path.exists():
        print(f'missing={path}')
        return

    df = pd.read_csv(path)
    folds, selected = run_walkforward_validation(
        df,
        min_train_rows=args.min_train_rows,
        test_days=args.test_days,
        step_days=args.step_days,
        min_evidence_score=args.min_evidence_score,
        max_folds=args.max_folds,
    )

    if folds.empty:
        print('walkforward=EMPTY')
        return

    out_folds = Path('data/walkforward_folds.csv')
    folds.to_csv(out_folds, index=False)
    print(f'saved={out_folds}')
    print('\n=== WALKFORWARD FOLDS ===')
    print(folds.to_string(index=False))

    if not selected.empty:
        out_selected = Path('data/walkforward_selected.csv')
        selected.to_csv(out_selected, index=False)
        print(f'\nsaved={out_selected}')
        ret5 = pd.to_numeric(selected.get('ret_5d'), errors='coerce').dropna()
        if not ret5.empty:
            print(f'selected_rows={len(selected)} avg5={(ret5.mean()*100):.4f}% hit5={((ret5>0).mean()*100):.2f}%')


if __name__ == '__main__':
    main()
