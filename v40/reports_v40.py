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
from v40.operability import VALID_SETUPS, DEFAULT_BASELINE_COOLDOWN_DAYS, DEFAULT_BASELINE_MAX_CONCURRENT, DEFAULT_SETUP_CAPS
from scripts.telegram.telegram_formatter import build_message


# ============================================================
# Utilidades
# ============================================================

def _ensure_date(d: date | None) -> date:
    return d or datetime.utcnow().date()


# ============================================================
# Mensaje diario — Señales E-Prime
# ============================================================

def build_daily_valid_setups_report(df_base: pd.DataFrame, ref_date: date | None = None) -> Tuple[str, str]:
    """
    Construye el mensaje diario para Cobra v4.0 basado solo en setups válidos operables.

    Retorna:
        (date_str, message_text)
    """
    ref_date = _ensure_date(ref_date)

    df_today = get_today_eprime_signals(df_base, ref_date=ref_date)
    if df_today.empty:
        df_today = df_base.copy()
        if 'signal_date' in df_today.columns:
            df_today['signal_date'] = pd.to_datetime(df_today['signal_date'], errors='coerce')
            df_today = df_today[df_today['signal_date'].dt.date == ref_date]

    if not df_today.empty:
        if 'signal_status' in df_today.columns:
            df_today = df_today[df_today['signal_status'] != 'disabled']
        if 'setup_code' in df_today.columns:
            df_today = df_today[df_today['setup_code'].isin(VALID_SETUPS)]

    n_signals = len(df_today)

    summary_lines: List[str] = [
        f"Setups válidos detectados hoy: {n_signals}",
        f"Baseline operativo sugerido: max {DEFAULT_BASELINE_MAX_CONCURRENT} posiciones / cooldown {DEFAULT_BASELINE_COOLDOWN_DAYS}d",
        f"Cupos por setup: US={DEFAULT_SETUP_CAPS.get('A_REV_US', '-')}, GLOBAL={DEFAULT_SETUP_CAPS.get('A_REV_GLOBAL', '-')}, D_EU={DEFAULT_SETUP_CAPS.get('D_EU_TACTICAL', '-')}",
    ]

    data_lines: List[str] = []

    if n_signals == 0:
        data_lines.append("Hoy no hay señales operables en los 3 setups validados.")
    else:
        data_lines.append("Detalle de señales operables priorizadas:")
        df_today = df_today.sort_values(by=[c for c in ['signal_score', 'quality_tier', 'ticker'] if c in df_today.columns], ascending=[False, True, True])
        for _, row in df_today.iterrows():
            ticker = row["ticker"]
            fam = row.get("pattern_family", "SETUP")
            setup = row.get("setup_code", "")
            quality = row.get("quality_tier", "")
            score = row.get("signal_score", "")
            target = row.get("target_price", None)
            stop = row.get("stop_price", None)
            super_flag = bool(row.get("is_supersignal_v40", False))
            super_type = row.get("supersignal_tipo_v40", "")

            extra = ""
            if setup:
                extra += f" · SETUP={setup}"
            if quality:
                extra += f" · Q={quality}"
            if score != "" and pd.notna(score):
                extra += f" · SCORE={int(score)}"
            if stop is not None and pd.notna(stop):
                extra += f" · STOP={float(stop):.2f}"
            if target is not None and pd.notna(target):
                extra += f" · TARGET={float(target):.2f}"
            if super_flag:
                extra += f" · SUPER={super_type or 'GENERICA'}"

            data_lines.append(f"• {ticker} [{fam}]{extra}")

    msg = build_message(
        phase="🐍 Cobra v4.0 · Diario Operable",
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
        data_lines.append("Resumen semanal por setup válido:")
        for _, row in summary.iterrows():
            fam = row["setup_code"]
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

