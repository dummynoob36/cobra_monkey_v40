"""
Motor diario de Cobra Monkey v4.0
---------------------------------
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, date
import pandas as pd

from v40.config_v40 import DAILY_PRICES_DIR, DATASET_V40_PATH, WEEKLY_WINDOW_DAYS
from v40.engine.fetch_daily_prices_v40 import run_daily_prices_v40
from v40.engine.build_dataset_v40 import build_dataset_v40
from v40.reports_v40 import build_daily_eprime_report, build_weekly_report
from scripts.tracking.tracking_engine_v40 import send_telegram_message


# ============================================================
# Asegurar PYTHONPATH
# ============================================================

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Utilidades
# ============================================================

def _today() -> date:
    return datetime.utcnow().date()


def _week_range(today: date):
    offset = today.weekday()
    monday = today - pd.Timedelta(days=offset)
    friday = monday + pd.Timedelta(days=WEEKLY_WINDOW_DAYS - 1)
    return monday.date(), friday.date()
    
# ============================================================
# RESUMEN SIMPLE AGRUPADO POR PATRÓN (v4.1)
# ============================================================

PATTERN_NAMES = {
    "A": "🟢 Sobreventa estructural",
    "B": "🟡 Rebote suave",
    "D": "🟠 Pullback controlado",
    "E": "🟣 Microcorrección / Compresión",
    "A_B": "🔵 Confluencia A+B",
    "A_B_D": "🔵 Confluencia A+B+D",
    "B_D": "🟠 Pullback + Rebote",
    "B_E": "🟣 Rebote + Compresión",
    "B_D_E": "🟣 Triple Confluencia B+D+E",
}


def _load_close_price(ticker: str, signal_date: date):
    csv_path = DAILY_PRICES_DIR / f"{ticker}.csv"
    if not csv_path.exists():
        return "N/A"

    df = pd.read_csv(csv_path)
    if "date" not in df.columns:
        return "N/A"

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    row = df[df["date"] == signal_date]

    if row.empty:
        # si falta la vela de ese día → usar última disponible
        px = float(df["close"].iloc[-1])
    else:
        px = float(row["close"].iloc[0])

    return f"{px:.1f}"   # devolver con 1 decimal


def build_simple_signal_summary(df_base: pd.DataFrame, ref_date: date) -> str:
    df_day = df_base[df_base["signal_date"].dt.date == ref_date]

    if df_day.empty:
        return f"📊 Señales Cobra v4.0 ({ref_date})\nSin señales hoy."

    # ---------------------------
    # 1) Agrupar por patrón
    # ---------------------------
    grouped = {}
    for _, row in df_day.iterrows():
        fam = row["pattern_family"]
        grouped.setdefault(fam, []).append(row["ticker"])

    # ---------------------------
    # 2) Construir mensaje
    # ---------------------------
    lines = [f"📊 Señales Cobra v4.0 ({ref_date})", ""]

    # Orden amigable de patrones
    pattern_order = [
        "A", "B", "D", "E",
        "A_B", "B_D", "B_E", "A_B_D", "B_D_E"
    ]

    for pat in pattern_order:
        if pat not in grouped:
            continue

        pat_name = PATTERN_NAMES.get(pat, pat)
        tickers = grouped[pat]

        # Título del patrón
        lines.append(f"{pat_name} ({pat})")
        for ticker in tickers:
            px = _load_close_price(ticker, ref_date)
            lines.append(f"• {ticker} @ {px}")

        lines.append("")  # salto visual entre grupos

    return "\n".join(lines).strip()



# ============================================================
# MOTOR PRINCIPAL
# ============================================================

def run_v40(no_telegram: bool = False) -> None:

    print("==============================================")
    print("🐍 Cobra Monkey v4.0 — Ejecución diaria")
    print("==============================================")

    today = _today()
    weekday = today.weekday()

    # --------------------------------------------------------
    # FASE 0
    # --------------------------------------------------------
    print(f"[V4] FASE 0 · Daily Prices ({today})")
    try:
        n_total, n_ok, failed, max_date = run_daily_prices_v40()
    except Exception as e:
        print(f"[V4][FASE 0][ERROR] {e}")
        print("[V4][FASE 0] Continuando…")

    # --------------------------------------------------------
    # FASE 1
    # --------------------------------------------------------
    print("[V4] FASE 1 · Construyendo dataset v40…")
    df_v40, start_date = build_dataset_v40()

    if df_v40.empty:
        print("[V4][FASE 1][WARN] dataset vacío.")
        return

    df_v40["signal_date"] = pd.to_datetime(df_v40["signal_date"], errors="coerce")
    df_v40 = df_v40.dropna(subset=["signal_date"])

    # --------------------------------------------------------
    # FASE 2 — Mensaje oficial
    # --------------------------------------------------------
    if weekday < 4:
        iso_date, msg = build_daily_eprime_report(df_v40, today)
    else:
        iso_date, msg = build_weekly_report(df_v40, today)

    print("\n================ MENSAJE COBRA v4.0 ================")
    print(msg)
    print("====================================================\n")

    # --------------------------------------------------------
    # FASE 2b — Resumen simple (Patrón–Ticker–Precio)
    # --------------------------------------------------------
    simple_msg = build_simple_signal_summary(df_v40, today)

    print("\n================ RESUMEN SIMPLE ================")
    print(simple_msg)
    print("================================================\n")

    # --------------------------------------------------------
    # FASE 3 — Envío Telegram
    # --------------------------------------------------------
    if not no_telegram:
        print("[V4] Enviando mensaje oficial…")
        send_telegram_message(msg)

        print("[V4] Enviando resumen simple…")
        send_telegram_message(simple_msg)
    else:
        print("[V4] --no-telegram activado.")

    print(f"[V4] Ejecución completa ({iso_date}).")


# ============================================================
if __name__ == "__main__":
    run_v40(no_telegram=False)

