"""
Lógica del motor Cobra Monkey v4.0
----------------------------------

Este módulo implementa la lógica de selección y filtrado de señales
ya presentes en el dataset v40.

Funciones principales:
    - get_today_eprime_signals()
    - get_weekly_signals_summary()

El dataset v40 contiene:
    signal_date, ticker, indicadores técnicos,
    pattern_family, is_e_prime_v40,
    is_supersignal_v40, supersignal_tipo_v40...

Este módulo NO calcula indicadores ni patrones;
solo filtra y agrupa lo que ya está calculado.
"""

from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Tuple

import pandas as pd

from v40.operability import VALID_SETUPS


# ============================================================
# Utilidades internas
# ============================================================

def _ensure_date(d: date | None) -> date:
    """Convierte None → hoy."""
    return d or datetime.utcnow().date()


# ============================================================
# Filtro de señales diarias (E-Prime)
# ============================================================

def get_today_eprime_signals(df: pd.DataFrame, ref_date: date | None = None) -> pd.DataFrame:
    """
    Retorna las señales E-Prime para la fecha indicada.

    Requiere columnas:
        - signal_date
        - ticker
        - pattern_family
        - is_e_prime_v40

    Retorna un DataFrame SOLO con las señales E-Prime del día.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    ref_date = _ensure_date(ref_date)

    df = df.copy()

    if "signal_date" not in df.columns:
        return pd.DataFrame()

    # Normalizamos fechas
    df["signal_date"] = pd.to_datetime(df["signal_date"], errors="coerce")
    df = df.dropna(subset=["signal_date"])
    df["signal_date_date"] = df["signal_date"].dt.date

    # Señales del día
    df_today = df[df["signal_date_date"] == ref_date]

    # Filtrar E-Prime
    if "is_e_prime_v40" not in df_today.columns:
        return pd.DataFrame()

    df_eprime = df_today[df_today["is_e_prime_v40"] == True].copy()

    if 'setup_code' in df_today.columns:
        df_valid = df_today[df_today['setup_code'].isin(VALID_SETUPS)].copy()
        if not df_valid.empty:
            df_eprime = pd.concat([df_eprime, df_valid], ignore_index=True).drop_duplicates()

    # Ordenar columnas
    cols = [
        "ticker",
        "signal_date",
        "pattern_family",
        "setup_code",
        "setup_note",
        "holding_horizon_days",
        "trade_style",
        "entry_price",
        "stop_price",
        "target_price",
        "signal_status",
        "market_bucket",
        "quality_tier",
        "quality_note",
        "signal_score",
        "signal_score_reasons",
        "is_supersignal_v40",
        "supersignal_tipo_v40",
    ]
    existing = [c for c in cols if c in df_eprime.columns]

    df_eprime = df_eprime[existing].sort_values("ticker")

    return df_eprime.reset_index(drop=True)


# ============================================================
# Resumen semanal de señales (todos los patrones)
# ============================================================

def get_weekly_signals_summary(
    df: pd.DataFrame,
    ref_date: date | None = None,
    window_days: int = 5,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Devuelve:

    df_week  → señales en [ref_date - window_days + 1, ref_date]
    summary  → agrupación por pattern_family con nº de señales

    Columnas requeridas:
        signal_date
        ticker
        pattern_family
    """
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    ref_date = _ensure_date(ref_date)

    df = df.copy()

    if "signal_date" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    df["signal_date"] = pd.to_datetime(df["signal_date"], errors="coerce")
    df = df.dropna(subset=["signal_date"])
    df["signal_date_date"] = df["signal_date"].dt.date

    start_date = ref_date - timedelta(days=window_days - 1)

    mask = (df["signal_date_date"] >= start_date) & (df["signal_date_date"] <= ref_date)
    df_week = df[mask].copy()

    if df_week.empty:
        return df_week, pd.DataFrame()

    if 'signal_status' in df_week.columns:
        df_week = df_week[df_week['signal_status'] != 'disabled']
    if 'setup_code' in df_week.columns:
        df_week = df_week[df_week['setup_code'].isin(VALID_SETUPS)]

    if df_week.empty:
        return df_week, pd.DataFrame()

    if "setup_code" not in df_week.columns:
        df_week["setup_code"] = "NONE"

    summary = (
        df_week
        .groupby(["setup_code"], dropna=False)
        .agg(n_signals=("ticker", "count"))
        .reset_index()
        .sort_values("n_signals", ascending=False)
    )

    return df_week.reset_index(drop=True), summary.reset_index(drop=True)

