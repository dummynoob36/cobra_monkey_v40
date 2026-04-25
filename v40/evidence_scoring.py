from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from v40.pattern_validation import enrich_dataset_with_forward_returns

DEFAULT_FORWARD_DAYS: tuple[int, ...] = (5, 10, 20)
MIN_SIGNALS_CONTEXT = 15
MIN_SIGNALS_SETUP = 40
RECENT_LOOKBACK_DAYS = 120


@dataclass(frozen=True)
class EvidenceScore:
    evidence_score: int
    evidence_label: str
    evidence_note: str
    context_signals: int
    setup_signals: int
    recent_context_signals: int
    recent_setup_signals: int


def _safe_mean_pct(series: pd.Series) -> float | None:
    series = pd.to_numeric(series, errors='coerce').dropna()
    if series.empty:
        return None
    return float(series.mean()) * 100.0


def _safe_hit_rate(series: pd.Series) -> float | None:
    series = pd.to_numeric(series, errors='coerce').dropna()
    if series.empty:
        return None
    return float((series > 0).mean()) * 100.0


def _build_context_key(df: pd.DataFrame) -> pd.Series:
    return (
        df['setup_code'].astype(str)
        + '|' + df['market_bucket'].astype(str)
        + '|' + df['trend_regime'].astype(str)
    )


def build_evidence_table(
    df_dataset: pd.DataFrame,
    forward_days: Iterable[int] = DEFAULT_FORWARD_DAYS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if df_dataset is None or df_dataset.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df_dataset.copy()
    required_cols = [f'ret_{int(h)}d' for h in forward_days if int(h) > 0]
    if not all(col in df.columns for col in required_cols):
        df = enrich_dataset_with_forward_returns(df, forward_days=forward_days)

    needed = {'setup_code', 'market_bucket', 'trend_regime', 'ticker', 'signal_date'}
    if not needed.issubset(df.columns):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df[df['setup_code'].astype(str) != 'DISABLED'].copy()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df['signal_date'] = pd.to_datetime(df['signal_date'], errors='coerce')
    df = df.dropna(subset=['signal_date']).copy()
    df['context_key'] = _build_context_key(df)

    def summarize(group_value: object, grp: pd.DataFrame, key_name: str) -> dict:
        ret5 = pd.to_numeric(grp.get('ret_5d'), errors='coerce')
        ret10 = pd.to_numeric(grp.get('ret_10d'), errors='coerce')
        ret20 = pd.to_numeric(grp.get('ret_20d'), errors='coerce')
        return {
            key_name: str(group_value),
            'signals': int(len(grp)),
            'unique_tickers': int(grp['ticker'].nunique()),
            'avg_return_5d': _safe_mean_pct(ret5),
            'avg_return_10d': _safe_mean_pct(ret10),
            'avg_return_20d': _safe_mean_pct(ret20),
            'hit_rate_5d': _safe_hit_rate(ret5),
            'hit_rate_10d': _safe_hit_rate(ret10),
            'hit_rate_20d': _safe_hit_rate(ret20),
        }

    setup_rows = [summarize(group_value, grp, 'setup_code') for group_value, grp in df.groupby('setup_code', dropna=False)]
    context_rows = [summarize(group_value, grp, 'context_key') for group_value, grp in df.groupby('context_key', dropna=False)]

    max_date = df['signal_date'].max()
    recent_cutoff = max_date - pd.Timedelta(days=RECENT_LOOKBACK_DAYS)
    recent_df = df[df['signal_date'] >= recent_cutoff].copy()

    recent_setup_rows = [summarize(group_value, grp, 'setup_code') for group_value, grp in recent_df.groupby('setup_code', dropna=False)] if not recent_df.empty else []
    recent_context_rows = [summarize(group_value, grp, 'context_key') for group_value, grp in recent_df.groupby('context_key', dropna=False)] if not recent_df.empty else []

    return (
        pd.DataFrame(setup_rows),
        pd.DataFrame(context_rows),
        pd.DataFrame(recent_setup_rows),
        pd.DataFrame(recent_context_rows),
    )


def score_row_with_evidence(
    row: pd.Series,
    setup_table: pd.DataFrame,
    context_table: pd.DataFrame,
    recent_setup_table: pd.DataFrame,
    recent_context_table: pd.DataFrame,
) -> EvidenceScore:
    setup = str(row.get('setup_code', ''))
    context_key = f"{setup}|{row.get('market_bucket', '')}|{row.get('trend_regime', '')}"

    setup_row = setup_table[setup_table['setup_code'].astype(str) == setup]
    context_row = context_table[context_table['context_key'].astype(str) == context_key]
    recent_setup_row = recent_setup_table[recent_setup_table['setup_code'].astype(str) == setup]
    recent_context_row = recent_context_table[recent_context_table['context_key'].astype(str) == context_key]

    setup_signals = int(setup_row['signals'].iloc[0]) if not setup_row.empty else 0
    context_signals = int(context_row['signals'].iloc[0]) if not context_row.empty else 0
    recent_setup_signals = int(recent_setup_row['signals'].iloc[0]) if not recent_setup_row.empty else 0
    recent_context_signals = int(recent_context_row['signals'].iloc[0]) if not recent_context_row.empty else 0

    score = 50.0
    notes: list[str] = []

    if not setup_row.empty:
        s = setup_row.iloc[0]
        avg5 = s.get('avg_return_5d')
        hit5 = s.get('hit_rate_5d')
        if pd.notna(avg5):
            score += min(15, max(-15, float(avg5) * 5))
            notes.append(f'setup_avg5={float(avg5):.2f}')
        if pd.notna(hit5):
            score += min(10, max(-10, (float(hit5) - 50) * 0.5))
            notes.append(f'setup_hit5={float(hit5):.1f}')
        if setup_signals < MIN_SIGNALS_SETUP:
            score -= 10
            notes.append('setup_sample_penalty')
    else:
        score -= 20
        notes.append('missing_setup_evidence')

    if not context_row.empty:
        c = context_row.iloc[0]
        avg5 = c.get('avg_return_5d')
        hit5 = c.get('hit_rate_5d')
        if pd.notna(avg5):
            score += min(20, max(-20, float(avg5) * 7))
            notes.append(f'ctx_avg5={float(avg5):.2f}')
        if pd.notna(hit5):
            score += min(12, max(-12, (float(hit5) - 50) * 0.6))
            notes.append(f'ctx_hit5={float(hit5):.1f}')
        if context_signals < MIN_SIGNALS_CONTEXT:
            score -= 15
            notes.append('context_sample_penalty')
    else:
        score -= 15
        notes.append('missing_context_evidence')

    if not recent_setup_row.empty and not setup_row.empty:
        recent_avg5 = recent_setup_row.iloc[0].get('avg_return_5d')
        long_avg5 = setup_row.iloc[0].get('avg_return_5d')
        if pd.notna(recent_avg5) and pd.notna(long_avg5):
            drift = float(recent_avg5) - float(long_avg5)
            if drift < -0.35:
                score -= 10
                notes.append(f'recent_setup_decay={drift:.2f}')
            elif drift > 0.20:
                score += 4
                notes.append(f'recent_setup_improve={drift:.2f}')

    if not recent_context_row.empty and not context_row.empty:
        recent_ctx_avg5 = recent_context_row.iloc[0].get('avg_return_5d')
        long_ctx_avg5 = context_row.iloc[0].get('avg_return_5d')
        if pd.notna(recent_ctx_avg5) and pd.notna(long_ctx_avg5):
            drift = float(recent_ctx_avg5) - float(long_ctx_avg5)
            if drift < -0.35:
                score -= 12
                notes.append(f'recent_context_decay={drift:.2f}')
            elif drift > 0.20:
                score += 5
                notes.append(f'recent_context_improve={drift:.2f}')

    score = max(0, min(100, int(round(score))))

    if score >= 75:
        label = 'STRONG'
    elif score >= 60:
        label = 'OK'
    else:
        label = 'WEAK'

    return EvidenceScore(
        evidence_score=score,
        evidence_label=label,
        evidence_note=','.join(notes),
        context_signals=context_signals,
        setup_signals=setup_signals,
        recent_context_signals=recent_context_signals,
        recent_setup_signals=recent_setup_signals,
    )


def annotate_with_evidence(df_dataset: pd.DataFrame) -> pd.DataFrame:
    if df_dataset is None or df_dataset.empty:
        return pd.DataFrame() if df_dataset is None else df_dataset.copy()

    setup_table, context_table, recent_setup_table, recent_context_table = build_evidence_table(df_dataset)
    out = df_dataset.copy()

    scored = out.apply(
        lambda row: score_row_with_evidence(row, setup_table, context_table, recent_setup_table, recent_context_table),
        axis=1,
    )
    out['evidence_score'] = [x.evidence_score for x in scored]
    out['evidence_label'] = [x.evidence_label for x in scored]
    out['evidence_note'] = [x.evidence_note for x in scored]
    out['context_signals'] = [x.context_signals for x in scored]
    out['setup_signals'] = [x.setup_signals for x in scored]
    out['recent_context_signals'] = [x.recent_context_signals for x in scored]
    out['recent_setup_signals'] = [x.recent_setup_signals for x in scored]
    return out


def build_setup_comparison_table(df_dataset: pd.DataFrame) -> pd.DataFrame:
    if df_dataset is None or df_dataset.empty:
        return pd.DataFrame()

    setup_table, _, recent_setup_table, _ = build_evidence_table(df_dataset)
    if setup_table.empty:
        return pd.DataFrame()

    out = setup_table.copy()
    out = out.rename(columns={
        'signals': 'signals_all',
        'unique_tickers': 'unique_tickers_all',
        'avg_return_5d': 'avg5_all',
        'avg_return_10d': 'avg10_all',
        'avg_return_20d': 'avg20_all',
        'hit_rate_5d': 'hit5_all',
        'hit_rate_10d': 'hit10_all',
        'hit_rate_20d': 'hit20_all',
    })

    if not recent_setup_table.empty:
        recent = recent_setup_table.rename(columns={
            'signals': 'signals_recent',
            'unique_tickers': 'unique_tickers_recent',
            'avg_return_5d': 'avg5_recent',
            'avg_return_10d': 'avg10_recent',
            'avg_return_20d': 'avg20_recent',
            'hit_rate_5d': 'hit5_recent',
            'hit_rate_10d': 'hit10_recent',
            'hit_rate_20d': 'hit20_recent',
        })
        out = out.merge(recent, on='setup_code', how='left')
    else:
        out['signals_recent'] = 0
        out['avg5_recent'] = pd.NA
        out['hit5_recent'] = pd.NA

    out['avg5_drift'] = pd.to_numeric(out.get('avg5_recent'), errors='coerce') - pd.to_numeric(out.get('avg5_all'), errors='coerce')
    out['hit5_drift'] = pd.to_numeric(out.get('hit5_recent'), errors='coerce') - pd.to_numeric(out.get('hit5_all'), errors='coerce')
    out = out.sort_values(['avg5_all', 'signals_all'], ascending=[False, False], na_position='last').reset_index(drop=True)
    return out
