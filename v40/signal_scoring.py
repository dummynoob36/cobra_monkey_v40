from __future__ import annotations

import math
import pandas as pd


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def compute_signal_score(row: pd.Series) -> tuple[int, str]:
    """
    Score heurístico inicial 0-100.
    Combina evidencia empírica observada + rasgos de cada señal.
    No sustituye un modelo validado walk-forward, pero permite ordenar mejor.
    """
    pattern = str(row.get('pattern_family', 'OTHER'))
    regime = str(row.get('trend_regime', 'UNKNOWN'))
    market = str(row.get('market_bucket', 'UNKNOWN'))
    quality = str(row.get('quality_tier', 'LOW'))

    score = 50.0
    reasons: list[str] = []

    quality_bonus = {
        'HIGH': 22,
        'MEDIUM': 10,
        'SPECULATIVE': 2,
        'LOW': -10,
        'AVOID': -25,
    }
    score += quality_bonus.get(quality, 0)
    reasons.append(f'quality={quality}')

    if pattern == 'A':
        score += 10
        reasons.append('pattern_A_positive_base')
        if market == 'US_OR_OTHER':
            score += 10
            reasons.append('A_US_strength')
        rsi = float(row.get('rsi14', math.nan))
        dist = float(row.get('dist_ema20_atr', math.nan))
        if not math.isnan(rsi) and rsi < 30:
            score += 4
            reasons.append('deep_oversold_rsi')
        if not math.isnan(dist) and dist < -2.5:
            score += 4
            reasons.append('deep_ema_dislocation')

    if pattern == 'E':
        score -= 20
        reasons.append('pattern_E_disabled')

    if pattern == 'D':
        score -= 10
        reasons.append('pattern_D_weak_base')
        if market == 'EU' and regime != 'RANGE':
            score += 18
            reasons.append('D_EU_context_rescue')

    if pattern in {'B', 'A_B', 'B_D', 'A_B_D'}:
        score -= 25
        reasons.append('disabled_pattern_family_penalty')

    if pattern in {'B_E', 'B_D_E'}:
        score -= 30
        reasons.append('disabled_pattern_penalty')

    if regime == 'RANGE' and pattern in {'D', 'B_E', 'B_D_E'}:
        score -= 8
        reasons.append('range_penalty')

    score = _clamp(score)
    return int(round(score)), ','.join(reasons)


def annotate_signal_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    out = df.copy()
    tuples = out.apply(compute_signal_score, axis=1)
    out['signal_score'] = [t[0] for t in tuples]
    out['signal_score_reasons'] = [t[1] for t in tuples]
    return out
