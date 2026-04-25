from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from v40.config_v40 import DATA_DIR
from v40.operability import VALID_SETUPS
from v40.pattern_quality import market_bucket_for_ticker
from v40.evidence_scoring import annotate_with_evidence

DAILY_CANDIDATES_PATH = DATA_DIR / 'daily_candidates.csv'

ALLOWED_QUALITY = {'HIGH', 'MEDIUM'}
ACTIVE_SETUPS = {'A_REV_US', 'D_EU_TACTICAL'}
MIN_SCORE_BY_SETUP: dict[str, int] = {
    'A_REV_US': 74,
    'D_EU_TACTICAL': 70,
}
MAX_CANDIDATES_BY_SETUP: dict[str, int] = {
    'A_REV_US': 3,
    'D_EU_TACTICAL': 2,
}
MAX_CANDIDATES_TOTAL = 5
MIN_DAYS_LISTED = 60
MIN_CLOSE_PRICE = 5.0
MIN_EVIDENCE_SCORE = 68


@dataclass(frozen=True)
class CandidateSelectionSummary:
    signal_date: str
    total_signals_seen: int
    eligible_after_filters: int
    final_candidates: int


def _to_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce')
    return out


def _quality_rank(value: str) -> int:
    order = {
        'HIGH': 3,
        'MEDIUM': 2,
        'SPECULATIVE': 1,
        'LOW': 0,
        'AVOID': -1,
    }
    return order.get(str(value), -1)


def _base_candidate_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out = _to_numeric(out, ['signal_score', 'close', 'rsi14', 'atr14'])

    if 'setup_code' in out.columns:
        out = out[out['setup_code'].isin(VALID_SETUPS)]
        out = out[out['setup_code'].isin(ACTIVE_SETUPS)]
    if 'signal_status' in out.columns:
        out = out[out['signal_status'] != 'disabled']
    if 'quality_tier' in out.columns:
        out = out[out['quality_tier'].isin(ALLOWED_QUALITY)]
    if 'close' in out.columns:
        out = out[out['close'].fillna(0) >= MIN_CLOSE_PRICE]
    if 'bars_count' in out.columns:
        out = out[out['bars_count'].fillna(0) >= MIN_DAYS_LISTED]
    if 'atr14' in out.columns:
        out = out[out['atr14'].notna() & (out['atr14'] > 0)]

    if 'setup_code' in out.columns and 'signal_score' in out.columns:
        out = out[
            out.apply(
                lambda r: float(r.get('signal_score', -999)) >= MIN_SCORE_BY_SETUP.get(str(r.get('setup_code')), 999),
                axis=1,
            )
        ]

    if {'setup_code', 'pattern_family', 'trend_regime', 'rsi14'}.issubset(out.columns):
        out = out[
            out.apply(_passes_context_rules, axis=1)
        ]

    return out


def _passes_context_rules(row: pd.Series) -> bool:
    setup = str(row.get('setup_code', ''))
    pattern = str(row.get('pattern_family', ''))
    regime = str(row.get('trend_regime', ''))
    market = str(row.get('market_bucket') or market_bucket_for_ticker(str(row.get('ticker', ''))))
    rsi = pd.to_numeric(pd.Series([row.get('rsi14')]), errors='coerce').iloc[0]

    if setup == 'A_REV_US':
        return pattern == 'A' and market == 'US_OR_OTHER' and regime == 'DOWN' and pd.notna(rsi) and rsi <= 28

    if setup == 'D_EU_TACTICAL':
        return pattern == 'D' and market == 'EU' and regime == 'DOWN' and pd.notna(rsi) and rsi <= 45

    return False


def build_daily_candidates(df_dataset: pd.DataFrame, ref_date=None) -> tuple[pd.DataFrame, CandidateSelectionSummary]:
    if df_dataset is None or df_dataset.empty:
        empty = pd.DataFrame()
        return empty, CandidateSelectionSummary(signal_date=str(ref_date or ''), total_signals_seen=0, eligible_after_filters=0, final_candidates=0)

    df = df_dataset.copy()
    if 'signal_date' not in df.columns:
        empty = pd.DataFrame()
        return empty, CandidateSelectionSummary(signal_date=str(ref_date or ''), total_signals_seen=0, eligible_after_filters=0, final_candidates=0)

    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')
    df = df.dropna(subset=['signal_date']).copy()
    if ref_date is None:
        ref_date = df['signal_date'].dt.date.max()

    df_day = df[df['signal_date'].dt.date == ref_date].copy()
    total_seen = len(df_day)

    if df_day.empty:
        empty = pd.DataFrame()
        return empty, CandidateSelectionSummary(signal_date=str(ref_date), total_signals_seen=total_seen, eligible_after_filters=0, final_candidates=0)

    if 'market_bucket' not in df_day.columns and 'ticker' in df_day.columns:
        df_day['market_bucket'] = df_day['ticker'].astype(str).map(market_bucket_for_ticker)

    enriched_day = df_day.copy()
    required_evidence_cols = {'ret_5d', 'ret_10d', 'ret_20d'}
    if required_evidence_cols.issubset(enriched_day.columns):
        try:
            enriched_day = annotate_with_evidence(df_day)
        except Exception:
            enriched_day = df_day.copy()
    eligible = _base_candidate_filters(enriched_day)
    if 'evidence_score' in eligible.columns:
        eligible = eligible[eligible['evidence_score'].fillna(0) >= MIN_EVIDENCE_SCORE]
    eligible_count = len(eligible)
    if eligible.empty:
        empty = pd.DataFrame(columns=df_day.columns)
        return empty, CandidateSelectionSummary(signal_date=str(ref_date), total_signals_seen=total_seen, eligible_after_filters=eligible_count, final_candidates=0)

    eligible = eligible.copy()
    eligible['quality_rank'] = eligible.get('quality_tier', '').map(_quality_rank)
    sort_cols = [c for c in ['evidence_score', 'signal_score', 'quality_rank', 'rsi14', 'ticker'] if c in eligible.columns]
    ascending = []
    for c in sort_cols:
        if c in {'evidence_score', 'signal_score', 'quality_rank'}:
            ascending.append(False)
        elif c == 'rsi14':
            ascending.append(True)
        else:
            ascending.append(True)
    eligible = eligible.sort_values(sort_cols, ascending=ascending)

    selected_parts = []
    for setup, cap in MAX_CANDIDATES_BY_SETUP.items():
        part = eligible[eligible['setup_code'] == setup].copy()
        if part.empty:
            continue
        if 'ticker' in part.columns:
            part = part.drop_duplicates(subset=['ticker'], keep='first')
        selected_parts.append(part.head(cap))

    if selected_parts:
        selected = pd.concat(selected_parts, ignore_index=True)
    else:
        selected = eligible.head(0).copy()

    if not selected.empty and 'ticker' in selected.columns:
        selected = selected.drop_duplicates(subset=['ticker'], keep='first')

    if not selected.empty:
        sort_cols_final = [c for c in ['evidence_score', 'signal_score', 'quality_rank', 'ticker'] if c in selected.columns]
        ascending_final = [False if c in {'evidence_score', 'signal_score', 'quality_rank'} else True for c in sort_cols_final]
        selected = selected.sort_values(sort_cols_final, ascending=ascending_final).head(MAX_CANDIDATES_TOTAL)

    selected = selected.drop(columns=['quality_rank'], errors='ignore').reset_index(drop=True)

    preferred_cols = [
        'signal_date', 'ticker', 'setup_code', 'pattern_family', 'trend_regime', 'market_bucket',
        'quality_tier', 'quality_note', 'signal_score', 'signal_score_reasons', 'evidence_score', 'evidence_label', 'evidence_note', 'context_signals', 'setup_signals', 'recent_context_signals', 'recent_setup_signals', 'close',
        'entry_price', 'stop_price', 'target_price', 'rsi14', 'atr14', 'setup_note'
    ]
    existing = [c for c in preferred_cols if c in selected.columns]
    trailing = [c for c in selected.columns if c not in existing]
    selected = selected[existing + trailing]

    return selected, CandidateSelectionSummary(
        signal_date=str(ref_date),
        total_signals_seen=total_seen,
        eligible_after_filters=eligible_count,
        final_candidates=len(selected),
    )


def save_daily_candidates(df_candidates: pd.DataFrame, path: Path = DAILY_CANDIDATES_PATH) -> Path:
    out = df_candidates.copy()
    out.to_csv(path, index=False)
    return path
