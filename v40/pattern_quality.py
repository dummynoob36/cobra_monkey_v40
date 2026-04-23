from __future__ import annotations

import pandas as pd


def market_bucket_for_ticker(ticker: str) -> str:
    euro_suffixes = ('.MC', '.DE', '.PA', '.SW', '.MI', '.LS', '.BR')
    return 'EU' if str(ticker).endswith(euro_suffixes) else 'US_OR_OTHER'


def classify_signal_quality(row: pd.Series) -> tuple[str, str]:
    """
    Clasificador heurístico inicial basado en la evidencia observada del dataset actual.
    Devuelve (quality_tier, quality_note).
    """
    pattern = str(row.get('pattern_family', 'OTHER'))
    regime = str(row.get('trend_regime', 'UNKNOWN'))
    market = market_bucket_for_ticker(str(row.get('ticker', '')))

    if pattern == 'A' and market == 'US_OR_OTHER':
        return 'HIGH', 'Patrón A en US/otros: mejor evidencia forward actual.'

    if pattern == 'A' and regime == 'DOWN':
        return 'MEDIUM', 'Patrón A en caída: hipótesis viva y razonable.'

    if pattern == 'D' and market == 'EU' and regime != 'RANGE':
        return 'MEDIUM', 'D_EU_TACTICAL es uno de los pocos setups rescatables.'

    if pattern in {'E', 'B', 'A_B', 'B_D', 'A_B_D', 'B_E', 'B_D_E'}:
        return 'AVOID', 'Patrón despriorizado o desactivado por falta de evidencia suficiente.'

    if pattern == 'D':
        return 'AVOID', 'Patrón D fuera del nicho EU táctico queda desactivado.'

    return 'LOW', 'Sin evidencia suficiente para priorizar esta señal.'


def annotate_signal_quality(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    out = df.copy()
    qualities = out.apply(classify_signal_quality, axis=1)
    out['quality_tier'] = [q[0] for q in qualities]
    out['quality_note'] = [q[1] for q in qualities]
    out['market_bucket'] = out['ticker'].astype(str).map(market_bucket_for_ticker)
    return out
