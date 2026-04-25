from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from v40.evidence_scoring import build_evidence_table, score_row_with_evidence
from v40.pattern_validation import enrich_dataset_with_forward_returns

DEFAULT_FORWARD_DAYS: tuple[int, ...] = (5, 10, 20)
DEFAULT_MIN_TRAIN_ROWS = 400
DEFAULT_TEST_DAYS = 30
DEFAULT_STEP_DAYS = 30
DEFAULT_MIN_EVIDENCE_SCORE = 60


@dataclass(frozen=True)
class WalkforwardFoldSummary:
    train_end: str
    test_start: str
    test_end: str
    test_rows: int
    selected_rows: int
    avg_return_5d: float | None
    hit_rate_5d: float | None


def _safe_pct(series: pd.Series) -> float | None:
    series = pd.to_numeric(series, errors='coerce').dropna()
    if series.empty:
        return None
    return round(float(series.mean()) * 100.0, 4)


def _safe_hit(series: pd.Series) -> float | None:
    series = pd.to_numeric(series, errors='coerce').dropna()
    if series.empty:
        return None
    return round(float((series > 0).mean()) * 100.0, 2)


def run_walkforward_validation(
    df_dataset: pd.DataFrame,
    forward_days: Iterable[int] = DEFAULT_FORWARD_DAYS,
    min_train_rows: int = DEFAULT_MIN_TRAIN_ROWS,
    test_days: int = DEFAULT_TEST_DAYS,
    step_days: int = DEFAULT_STEP_DAYS,
    min_evidence_score: int = DEFAULT_MIN_EVIDENCE_SCORE,
    max_folds: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df_dataset is None or df_dataset.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = df_dataset.copy()
    if 'signal_date' not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    required_cols = [f'ret_{int(h)}d' for h in forward_days if int(h) > 0]
    if not all(col in df.columns for col in required_cols):
        df = enrich_dataset_with_forward_returns(df, forward_days=forward_days)

    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')
    df = df.dropna(subset=['signal_date']).sort_values('signal_date').reset_index(drop=True)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    unique_days = sorted(df['signal_date'].dt.date.unique())
    if len(unique_days) < 2:
        return pd.DataFrame(), pd.DataFrame()

    fold_rows: list[dict] = []
    selected_rows_all: list[pd.DataFrame] = []

    fold_count = 0

    for idx in range(0, len(unique_days), max(1, int(step_days))):
        test_start = unique_days[idx]
        train_df = df[df['signal_date'].dt.date < test_start].copy()
        if len(train_df) < min_train_rows:
            continue

        test_end_idx = min(len(unique_days), idx + test_days)
        test_window_days = set(unique_days[idx:test_end_idx])
        test_df = df[df['signal_date'].dt.date.isin(test_window_days)].copy()
        if test_df.empty:
            continue

        setup_table, context_table, recent_setup_table, recent_context_table = build_evidence_table(train_df)
        if setup_table.empty:
            continue

        scored = test_df.copy()
        evidence = scored.apply(lambda row: score_row_with_evidence(row, setup_table, context_table, recent_setup_table, recent_context_table), axis=1)
        scored['wf_evidence_score'] = [x.evidence_score for x in evidence]
        scored['wf_evidence_label'] = [x.evidence_label for x in evidence]

        selected = scored[scored['wf_evidence_score'] >= min_evidence_score].copy()
        if not selected.empty:
            selected_rows_all.append(selected)

        fold_rows.append({
            'fold_index': fold_count,
            'train_end': str(max(train_df['signal_date'].dt.date)),
            'test_start': str(min(test_window_days)),
            'test_end': str(max(test_window_days)),
            'test_rows': int(len(test_df)),
            'selected_rows': int(len(selected)),
            'avg_return_5d': _safe_pct(selected.get('ret_5d', pd.Series(dtype=float))),
            'hit_rate_5d': _safe_hit(selected.get('ret_5d', pd.Series(dtype=float))),
        })

        fold_count += 1
        if max_folds is not None and fold_count >= max_folds:
            break

    folds_df = pd.DataFrame(fold_rows)
    selected_df = pd.concat(selected_rows_all, ignore_index=True) if selected_rows_all else pd.DataFrame()
    return folds_df, selected_df
