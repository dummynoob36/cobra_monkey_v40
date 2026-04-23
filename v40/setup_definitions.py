from __future__ import annotations

import math
import pandas as pd

from v40.operability import VALID_SETUPS, get_exit_policy


def _safe_float(value) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def derive_setup(row: pd.Series) -> tuple[str, str, int]:
    pattern = str(row.get('pattern_family', 'OTHER'))
    regime = str(row.get('trend_regime', 'UNKNOWN'))
    market = str(row.get('market_bucket', 'UNKNOWN'))

    rsi = _safe_float(row.get('rsi14'))

    if pattern == 'A' and market == 'US_OR_OTHER' and rsi is not None and rsi < 28:
        policy = get_exit_policy('A_REV_US')
        return 'A_REV_US', 'Reversal de sobreventa estructural en US/otros con RSI profundo.', policy.horizon_days if policy else 10

    if pattern == 'A' and rsi is not None and rsi < 30:
        policy = get_exit_policy('A_REV_GLOBAL')
        return 'A_REV_GLOBAL', 'Reversal de sobreventa estructural global con RSI filtrado.', policy.horizon_days if policy else 15

    if pattern == 'D' and market == 'EU' and regime != 'RANGE':
        policy = get_exit_policy('D_EU_TACTICAL')
        return 'D_EU_TACTICAL', 'Pullback táctico europeo en contexto específico.', policy.horizon_days if policy else 7

    return 'DISABLED', 'Patrón desactivado por falta de evidencia suficiente.', 0


def derive_trade_plan(row: pd.Series) -> tuple[str, float | None, float | None, float | None]:
    close = _safe_float(row.get('close'))
    atr = _safe_float(row.get('atr14'))
    if close is None or atr is None or atr <= 0:
        return 'close_confirmation', None, None, None

    setup, _, _ = derive_setup(row)
    policy = get_exit_policy(setup)

    if policy is not None:
        entry = close
        stop = close - policy.stop_atr_mult * atr
        target = close + policy.target_atr_mult * atr
        return policy.exit_style, entry, stop, target

    if setup == 'DISABLED':
        return 'disabled', None, None, None

    entry = close
    stop = close - 1.0 * atr
    target = close + 1.5 * atr
    return 'generic_pattern_trade', entry, stop, target


def annotate_setups(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    out = df.copy()
    setups = out.apply(derive_setup, axis=1)
    out['setup_code'] = [s[0] for s in setups]
    out['setup_note'] = [s[1] for s in setups]
    out['holding_horizon_days'] = [s[2] for s in setups]

    plans = out.apply(derive_trade_plan, axis=1)
    out['trade_style'] = [p[0] for p in plans]
    out['entry_price'] = [p[1] for p in plans]
    out['stop_price'] = [p[2] for p in plans]
    out['target_price'] = [p[3] for p in plans]
    out['signal_status'] = out['setup_code'].map(lambda s: 'new' if s in VALID_SETUPS else 'disabled')
    return out
