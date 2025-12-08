"""
Generación de mensajes de reporte para Cobra v4.0
-------------------------------------------------

Este módulo se encarga de construir:

1. Mensaje diario (E-Prime)
2. Mensaje semanal (resumen por patrones)

Usa como base el dataset v40 ya procesado por:
    v40/engine/build_dataset_v40.py

Y filtra datos mediante:
    v40/engine_v40.py

El resultado final se envía a Telegram mediante tracking_engine_v40.py
o se muestra en consola cuando run_v40.py se ejecuta con --no-telegram.
"""

from __future__ import annotations
from datetime import datetime, date
from typing import List, Tuple

import pandas as pd

from v40.engine_v40 import (
    get_today_eprime_signals,
    get_weekly_signals_summary,
)
from scripts.telegram.telegram_formatter import build_message


# ============================================================
# Utilidades
# ============================================================

def _ensure_date(d: date | None) -> date:
    return d or datetime.utcnow().date()


# ============================================================
# Mensaje diario — Señales E-Prime
# ============================================================

def build_daily_eprime_report(df_base: pd.DataFrame, ref_date: date | None = None) -> Tuple[str, str]:
    """
    Construye el mensaje diario para Cobra v4.0 basado en señales E-Prime.

    Retorna:
        (date_str, message_text)
    """
    ref_date = _ensure_date(ref_date)

    df_eprime = get_today_eprime_signals(df_base, ref_date=ref_date)
    n_eprime = len(df_eprime)

    summary_lines: List[str] = [
        f"Señales E-Prime detectadas hoy: {n_eprime}",
    ]

    data_lines: List[str] = []

    if n_eprime == 0:
        data_lines.append("Hoy no hay señales E-Prime en v4.0.")
    else:
        data_lines.append("Detalle de señales E-Prime:")
        for _, row in df_eprime.iterrows():
            ticker = row["ticker"]
            fam = row.get("pattern_family", "E_PRIME")
            super_flag = bool(row.get("is_supersignal_v40", False))
            super_type = row.get("supersignal_tipo_v40", "")

            extra = ""
            if super_flag:
                extra = f" · SUPER={super_type or 'GENERICA'}"

            data_lines.append(f"• {ticker} [{fam}]{extra}")

    msg = build_message(
        phase="🐍 Cobra v4.0 · Diario (E-Prime)",
        date=ref_date.isoformat(),
        status="OK",
        summary_lines=summary_lines,
        data_lines=data_lines,
    )

    return ref_date.isoformat(), msg


# ============================================================
# Mensaje semanal — Resumen por patrones
# ============================================================

def build_weekly_report(df_base: pd.DataFrame, ref_date: date | None = None) -> Tuple[str, str]:
    """
    Construye mensaje semanal del sistema Cobra v4.0.

    Resumen:
        - nº total de señales en la semana
        - agrupación por pattern_family
    """
    ref_date = _ensure_date(ref_date)

    df_week, summary = get_weekly_signals_summary(df_base, ref_date=ref_date, window_days=5)

    n_total = len(df_week)
    summary_lines: List[str] = [
        f"Señales totales detectadas en la semana (L–V): {n_total}",
    ]

    data_lines: List[str] = []

    if summary is None or summary.empty:
        data_lines.append("No hay señales registradas en la ventana semanal.")
    else:
        data_lines.append("Resumen semanal por patrón:")
        for _, row in summary.iterrows():
            fam = row["pattern_family"]
            n = int(row["n_signals"])
            data_lines.append(f"• {fam}: {n}")

    msg = build_message(
        phase="🐍 Cobra v4.0 · Resumen Semanal",
        date=ref_date.isoformat(),
        status="OK",
        summary_lines=summary_lines,
        data_lines=data_lines,
    )

    return ref_date.isoformat(), msg

