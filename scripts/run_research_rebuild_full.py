from __future__ import annotations

from pathlib import Path

from v40.engine.build_research_dataset_v40 import build_research_dataset_v40
from v40.pattern_validation import summarize_pattern_validation
from v40.setup_validation import summarize_setup_validation


def main() -> None:
    df = build_research_dataset_v40()
    print(f'research_rows={len(df)}')
    if df.empty:
        return

    out_path = Path('data/dataset_v40_research_full.csv')
    df.to_csv(out_path, index=False)
    print(f'saved={out_path}')

    pat = summarize_pattern_validation(df)
    setup = summarize_setup_validation(df)

    print('\n=== PATTERN VALIDATION (RESEARCH FULL) ===')
    print(pat.to_string(index=False))
    print('\n=== SETUP VALIDATION (RESEARCH FULL) ===')
    print(setup.to_string(index=False))

    min_signals = 20
    pat_f = pat[pat['signals'] >= min_signals]
    setup_f = setup[setup['signals'] >= min_signals]

    if not pat_f.empty:
        print(f'\n=== TOP PATTERNS AVG5 (min {min_signals}) ===')
        print(pat_f.sort_values('avg_return_5d', ascending=False).to_string(index=False))

    if not setup_f.empty:
        print(f'\n=== TOP SETUPS AVG5 (min {min_signals}) ===')
        print(setup_f.sort_values('avg_return_5d', ascending=False).to_string(index=False))
        print(f'\n=== TOP SETUPS AVG20 (min {min_signals}) ===')
        print(setup_f.sort_values('avg_return_20d', ascending=False).to_string(index=False))


if __name__ == '__main__':
    main()
