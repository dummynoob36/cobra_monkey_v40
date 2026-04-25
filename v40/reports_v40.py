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
from v40.daily_candidates import build_daily_candidates
from scripts.telegram.telegram_formatter import build_message


def _bucket_label(bucket: str) -> str:
    return 'US/Other' if str(bucket) == 'US_OR_OTHER' else str(bucket)


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

    df_today, selection_summary = build_daily_candidates(df_base, ref_date=ref_date)
    n_signals = len(df_today)

    summary_lines: List[str] = [
        f"Señales vistas hoy: {selection_summary.total_signals_seen}",
        f"Elegibles tras filtros estrictos: {selection_summary.eligible_after_filters}",
        f"Candidatas finales: {selection_summary.final_candidates}",
        "Política: no forzar señales si no superan calidad + contexto + score.",
    ]

    data_lines: List[str] = []

    if n_signals == 0:
        data_lines.append("Hoy no hay candidatas con calidad suficiente. Eso es correcto.")
    else:
        data_lines.append("Top candidatas del día:")
        if 'market_bucket' in df_today.columns:
            grouped = list(df_today.groupby('market_bucket', dropna=False))
        else:
            grouped = [('ALL', df_today)]

        for bucket, grp in grouped:
            data_lines.append(f"")
            data_lines.append(f"{_bucket_label(bucket)}")
            grp = grp.sort_values(
                by=[c for c in ['evidence_score', 'signal_score', 'ticker'] if c in grp.columns],
                ascending=[False, False, True][:len([c for c in ['evidence_score', 'signal_score', 'ticker'] if c in grp.columns])]
            )
            for _, row in grp.iterrows():
                ticker = row["ticker"]
                setup = row.get("setup_code", "")
                quality = row.get("quality_tier", "")
                score = row.get("signal_score", "")
                evidence = row.get("evidence_score", "")
                target = row.get("target_price", None)
                stop = row.get("stop_price", None)
                close = row.get("close", None)
                note = str(row.get("setup_note", "")).strip()

                parts = [ticker]
                if setup:
                    parts.append(f"{setup}")
                if quality:
                    parts.append(f"Q={quality}")
                if score != "" and pd.notna(score):
                    parts.append(f"S={int(score)}")
                if evidence != "" and pd.notna(evidence):
                    parts.append(f"E={int(evidence)}")
                if close is not None and pd.notna(close):
                    parts.append(f"C={float(close):.2f}")
                if stop is not None and pd.notna(stop):
                    parts.append(f"ST={float(stop):.2f}")
                if target is not None and pd.notna(target):
                    parts.append(f"TG={float(target):.2f}")

                data_lines.append(f"• {' · '.join(parts)}")
                if note:
                    data_lines.append(f"  ↳ {note}")

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

