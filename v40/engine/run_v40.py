"""
Motor diario de Cobra Monkey v4.0
---------------------------------

Ejecuta automáticamente:

FASE 0 → Actualizar daily prices (core v3.x)
FASE 1 → Construir / actualizar dataset v40
FASE 2 → Generar mensaje diario (L–J) o semanal (V)
FASE 3 → Enviar mensaje a Telegram (opcional)

Este archivo es el PUNTO DE ENTRADA PRINCIPAL del sistema.
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, date
import pandas as pd

from v40.config_v40 import DATASET_V40_PATH, WEEKLY_WINDOW_DAYS
from v40.engine.fetch_daily_prices_v40 import run_daily_prices_v40
from v40.engine.build_dataset_v40 import build_dataset_v40
from v40.reports_v40 import build_daily_eprime_report, build_weekly_report
from scripts.tracking.tracking_engine_v40 import send_telegram_message


# ============================================================
# Asegurar que la raíz del repo está en sys.path
# ============================================================

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Utilidades internas
# ============================================================

def _today() -> date:
    return datetime.utcnow().date()


def _week_range(today: date):
    """Devuelve el rango L–V que contiene `today`."""
    offset = today.weekday()  # Monday=0
    monday = today - pd.Timedelta(days=offset)
    friday = monday + pd.Timedelta(days=WEEKLY_WINDOW_DAYS - 1)
    return monday.date(), friday.date()


# ============================================================
# MOTOR PRINCIPAL
# ============================================================

def run_v40(no_telegram: bool = False) -> None:
    """
    Ejecuta el flujo completo diario del sistema Cobra v4.0.
    """
    print("==============================================")
    print("🐍 Cobra Monkey v4.0 — Ejecución diaria")
    print("==============================================")

    today = _today()
    weekday = today.weekday()  # Monday=0, Friday=4

    # --------------------------------------------------------
    # FASE 0 — Daily Prices
    # --------------------------------------------------------
    print(f"[V4] FASE 0 · Daily Prices ({today})")
    try:
        n_total, n_ok, failed, max_date = run_daily_prices_v40()
    except Exception as e:
        print(f"[V4][FASE 0][ERROR] Error inesperado: {e}")
        print("[V4][FASE 0] Continuando ejecución…")

    # --------------------------------------------------------
    # FASE 1 — Dataset v40
    # --------------------------------------------------------
    print(f"[V4] FASE 1 · Construyendo dataset v40…")
    df_v40, start_date = build_dataset_v40()

    if df_v40.empty:
        print("[V4][FASE 1][WARN] dataset_v40 vacío. No hay nada que reportar.")
        return

    df_v40["signal_date"] = pd.to_datetime(df_v40["signal_date"], errors="coerce")
    df_v40 = df_v40.dropna(subset=["signal_date"])

    # --------------------------------------------------------
    # FASE 2 — Mensajería
    # --------------------------------------------------------
    if weekday < 4:
        # Lunes–Jueves → mensaje diario E-Prime
        print("[V4] FASE 2 · Generando mensaje diario (E-Prime)…")
        iso_date, msg = build_daily_eprime_report(df_v40, today)

    elif weekday == 4:
        # Viernes → mensaje semanal
        print("[V4] FASE 2 · Generando mensaje semanal…")
        iso_date, msg = build_weekly_report(df_v40, today)

    else:
        # Fin de semana
        print("[V4] Hoy es fin de semana. No se genera mensaje.")
        return

    print("\n================ MENSAJE COBRA v4.0 ================")
    print(msg)
    print("====================================================\n")

    # --------------------------------------------------------
    # FASE 2b — Resumen simple de señales (Patrón–Ticker–Precio)
    # --------------------------------------------------------
    def build_simple_signal_summary(df_base, ref_date):
        df_day = df_base[df_base["signal_date"].dt.date == ref_date]

        if df_day.empty:
            return f"📊 Señales Cobra v4.0 ({ref_date})\nSin señales hoy."

        lines = [f"📊 Señales Cobra v4.0 ({ref_date})", ""]

        for _, row in df_day.iterrows():
            fam = row["pattern_family"]
            tick = row["ticker"]
            price = row["close"] if "close" in row else "N/A"
            lines.append(f"{fam} → {tick} @ {price}")

        return "\n".join(lines)


    # justo después del mensaje principal
    simple_msg = build_simple_signal_summary(df_v40, today)

    print("\n================ RESUMEN SIMPLE ================")
    print(simple_msg)
    print("================================================\n")

    if not no_telegram:
        send_telegram_message(simple_msg)



    # --------------------------------------------------------
    # FASE 3 — Envío a Telegram
    # --------------------------------------------------------
    if not no_telegram:
        print("[V4] Enviando mensaje a Telegram…")
        send_telegram_message(msg)
    else:
        print("[V4] --no-telegram activado. Mensaje NO enviado.")

    print(f"[V4] Ejecución completa ({iso_date}).")


# ============================================================
# Ejecución directa
# ============================================================

if __name__ == "__main__":
    run_v40(no_telegram=False)

