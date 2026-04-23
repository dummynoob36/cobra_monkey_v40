from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from v40.pattern_validation import enrich_dataset_with_forward_returns

DEFAULT_FORWARD_DAYS: tuple[int, ...] = (5, 10, 20)


@dataclass(frozen=True)
class SetupValidationSummary:
    setup_code: str
    signals: int
    unique_tickers: int
    hit_rate_5d: float | None
    avg_return_5d: float | None
    median_return_5d: float | None
    avg_return_10d: float | None
    avg_return_20d: float | None


def _safe_pct(series: pd.Series) -> float | None:
    series = pd.to_numeric(series, errors='coerce')
    if series.dropna().empty:
        return None
    return round(float(series.mean()) * 100, 4)


def summarize_setup_validation(
    df_dataset: pd.DataFrame,
    forward_days: Iterable[int] = DEFAULT_FORWARD_DAYS,
) -> pd.DataFrame:
    if df_dataset is None or df_dataset.empty:
        return pd.DataFrame()

    df = df_dataset.copy()
    required_return_cols = [f'ret_{int(h)}d' for h in forward_days if int(h) > 0]
    if not all(col in df.columns for col in required_return_cols):
        df = enrich_dataset_with_forward_returns(df, forward_days=forward_days)

    if 'setup_code' not in df.columns:
        return pd.DataFrame()

    rows: list[SetupValidationSummary] = []
    for setup_code, grp in df.groupby('setup_code', dropna=False):
        ret5 = pd.to_numeric(grp.get('ret_5d'), errors='coerce')
        ret10 = pd.to_numeric(grp.get('ret_10d'), errors='coerce')
        ret20 = pd.to_numeric(grp.get('ret_20d'), errors='coerce')

        hit5 = None
        if not ret5.dropna().empty:
            hit5 = round(float((ret5 > 0).mean()) * 100, 2)

        rows.append(
            SetupValidationSummary(
                setup_code=str(setup_code),
                signals=int(len(grp)),
                unique_tickers=int(grp['ticker'].nunique()) if 'ticker' in grp else 0,
                hit_rate_5d=hit5,
                avg_return_5d=_safe_pct(ret5),
                median_return_5d=(round(float(ret5.median()) * 100, 4) if not ret5.dropna().empty else None),
                avg_return_10d=_safe_pct(ret10),
                avg_return_20d=_safe_pct(ret20),
            )
        )

    out = pd.DataFrame([r.__dict__ for r in rows])
    if out.empty:
        return out

    return out.sort_values(['avg_return_5d', 'signals'], ascending=[False, False], na_position='last').reset_index(drop=True)
