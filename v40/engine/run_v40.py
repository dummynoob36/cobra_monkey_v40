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
from v40.reports_v40 import build_daily_valid_setups_report, build_weekly_report
from v40.daily_candidates import build_daily_candidates, save_daily_candidates
from v40.portfolio import close_positions_with_market_data, generate_entry_records, load_portfolio, save_portfolio, select_entries
from v40.telegram_ops import build_entry_alert, build_exit_alert, build_portfolio_status_alert
from scripts.tracking.tracking_engine_v40 import send_telegram_message


# ============================================================
# Asegurar PYTHONPATH
# ============================================================

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Carpeta de histórico v4.0
HISTORY_DIR = PROJECT_ROOT / "v40" / "history"


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


def _ensure_history_dir() -> Path:
    """
    Crea la carpeta de histórico si no existe y la devuelve.
    """
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return HISTORY_DIR


def _safe_date_token(analysis_date: str | date) -> str:
    """
    Normaliza la fecha para usarla en nombres de fichero.
    """
    token = str(analysis_date)
    # Por si en algún momento usamos "YYYY-MM-DD (week)" o similar,
    # limpiamos espacios y caracteres raros.
    token = token.replace(" ", "_").replace(":", "-").replace("/", "-")
    return token


def _save_daily_artifacts(
    analysis_date: str | date,
    df_v40: pd.DataFrame,
    official_msg: str,
    simple_msg: str,
) -> None:
    """
    Guarda:
      - Snapshot del dataset v40 en CSV
      - Mensaje oficial en TXT
      - Resumen simple en TXT
    para la fecha de análisis indicada.
    """
    try:
        hist_dir = _ensure_history_dir()
        date_token = _safe_date_token(analysis_date)

        # 1) Snapshot del dataset
        snapshot_path = hist_dir / f"dataset_v40_{date_token}.csv"
        df_copy = df_v40.copy()
        df_copy.to_csv(snapshot_path, index=False)

        # 2) Mensaje oficial
        official_path = hist_dir / f"message_official_{date_token}.txt"
        official_path.write_text(official_msg, encoding="utf-8")

        # 3) Resumen simple
        simple_path = hist_dir / f"summary_simple_{date_token}.txt"
        simple_path.write_text(simple_msg, encoding="utf-8")

        print(f"[V4][HISTORY] Artifacts guardados en {hist_dir} para {date_token}")

    except Exception as e:
        # No queremos que un fallo de escritura rompa todo el motor
        print(f"[V4][HISTORY][WARN] No se pudieron guardar los artifacts de histórico: {e}")


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

QUALITY_ICONS = {
    "HIGH": "🔥",
    "MEDIUM": "✅",
    "SPECULATIVE": "🧪",
    "LOW": "⚪",
    "AVOID": "⛔",
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


def compute_pattern_performance(df_dataset: pd.DataFrame):
    """
    Devuelve un dict con el rendimiento por patrón:
    { pattern: (ret_sin_repetir, ret_con_repetir) }
    """
    results = {}
    today = df_dataset["signal_date"].max().date()

    for pattern in df_dataset["pattern_family"].unique():
        df_pat = df_dataset[df_dataset["pattern_family"] == pattern]

        if df_pat.empty:
            results[pattern] = (0.0, 0.0)
            continue

        # --- rendimiento sin repetir (por ticker único)
        perf_unique = []
        for ticker in df_pat["ticker"].unique():
            row0 = df_pat[df_pat["ticker"] == ticker].iloc[0]
            signal_date = row0["signal_date"].date()
            price_signal = _load_close_price(ticker, signal_date)
            price_now = _load_close_price(ticker, today)

            if price_signal != "N/A" and price_now != "N/A":
                perf_unique.append((float(price_now) / float(price_signal)) - 1)

        ret_unique = round(sum(perf_unique) / len(perf_unique), 4) if perf_unique else 0.0

        # --- rendimiento reinvirtiendo en todas las señales
        perf_repeat = []
        for _, row in df_pat.iterrows():
            ticker = row["ticker"]
            signal_date = row["signal_date"].date()
            price_signal = _load_close_price(ticker, signal_date)
            price_now = _load_close_price(ticker, today)

            if price_signal != "N/A" and price_now != "N/A":
                perf_repeat.append((float(price_now) / float(price_signal)) - 1)

        ret_repeat = round(sum(perf_repeat) / len(perf_repeat), 4) if perf_repeat else 0.0

        results[pattern] = (ret_unique * 100, ret_repeat * 100)

    return results


def compute_pattern_sample_sizes(df_base: pd.DataFrame) -> dict:
    """
    Devuelve para cada patrón:
    - n_unique: número de tickers distintos que dieron señal
    - n_total: número total de señales (incluye duplicados)
    """
    result = {}
    patterns = df_base["pattern_family"].unique()

    for pat in patterns:
        df_p = df_base[df_base["pattern_family"] == pat]

        # tickers únicos (sin repetir)
        n_unique = df_p["ticker"].nunique()

        # señales totales (cada fila es una señal)
        n_total = len(df_p)

        result[pat] = (n_unique, n_total)

    return result


def build_simple_signal_summary(df_base: pd.DataFrame, ref_date: date) -> str:
    df_day = df_base[
        (df_base["signal_date"].dt.date == ref_date)
        & (df_base.get("signal_status", "new") != "disabled")
    ]

    if df_day.empty:
        return f"📊 Señales Cobra v4.0 ({ref_date})\nSin señales hoy."

    # obtener métricas de rendimiento
    perf = compute_pattern_performance(df_base)

    # nuevo: obtener tamaños de muestra
    sample_sizes = compute_pattern_sample_sizes(df_base)

    grouped = {}
    for _, row in df_day.iterrows():
        pat = row["pattern_family"]
        grouped.setdefault(pat, []).append(row)

    lines = [f"📊 Señales Cobra v4.0 ({ref_date})", ""]

    pattern_order = [
        "A", "B", "D", "E",
        "A_B", "B_D", "B_E", "A_B_D", "B_D_E"
    ]

    for pat in pattern_order:
        if pat not in grouped:
            continue

        pat_name = PATTERN_NAMES.get(pat, pat)

        # rendimiento
        ret_u, ret_r = perf.get(pat, (0.0, 0.0))

        # tamaños de muestra
        n_unique, n_total = sample_sizes.get(pat, (0, 0))

        ret_txt = f" ({ret_u:.2f}% | {ret_r:.2f}%)"
        size_txt = f" [{n_unique} | {n_total} señales]"

        # cabecera del patrón
        lines.append(f"{pat_name} ({pat}){ret_txt}{size_txt}")

        # tickers del día
        rows = sorted(
            grouped[pat],
            key=lambda r: (
                {"HIGH": 0, "MEDIUM": 1, "SPECULATIVE": 2, "LOW": 3, "AVOID": 4}.get(r.get("quality_tier", "LOW"), 9),
                -float(r.get("signal_score", 0) or 0),
                str(r.get("ticker", "")),
            )
        )

        for row in rows:
            ticker = row["ticker"]
            px = _load_close_price(ticker, ref_date)
            quality = row.get("quality_tier", "")
            score = row.get("signal_score", "")
            setup = row.get("setup_code", "")
            horizon = row.get("holding_horizon_days", "")
            q_icon = QUALITY_ICONS.get(quality, "")
            quality_txt = f" {q_icon}{quality}" if quality else ""
            score_txt = f" [{int(score)}]" if score != "" and pd.notna(score) else ""
            setup_txt = f" <{setup}>" if setup else ""
            horizon_txt = f" {int(horizon)}d" if horizon != "" and pd.notna(horizon) else ""
            lines.append(f"• {ticker} @ {px}{quality_txt}{score_txt}{setup_txt}{horizon_txt}")

        lines.append("")

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

    daily_candidates, candidate_summary = build_daily_candidates(df_v40, today)
    save_daily_candidates(daily_candidates)
    print(
        f"[V4] daily_candidates: seen={candidate_summary.total_signals_seen} "
        f"eligible={candidate_summary.eligible_after_filters} final={candidate_summary.final_candidates}"
    )

    # --------------------------------------------------------
    # FASE 2 — Mensaje oficial
    # --------------------------------------------------------
    if weekday < 4:
        iso_date, msg = build_daily_valid_setups_report(df_v40, today)
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
    # FASE 2c — Cartera viva: cierres + nuevas entradas
    # --------------------------------------------------------
    portfolio = load_portfolio()
    portfolio, closed_positions = close_positions_with_market_data(portfolio, as_of=pd.to_datetime(today))

    today_signals = daily_candidates.copy()
    selected_entries = select_entries(today_signals, portfolio)
    new_records = generate_entry_records(selected_entries)
    if not new_records.empty:
        portfolio = pd.concat([portfolio, new_records], ignore_index=True)

    save_portfolio(portfolio)

    entry_msg = build_entry_alert(selected_entries, iso_date)
    exit_msg = build_exit_alert(closed_positions, iso_date)
    portfolio_msg = build_portfolio_status_alert(portfolio, iso_date)

    # --------------------------------------------------------
    # FASE 2d — Guardar histórico local (dataset + mensajes)
    # --------------------------------------------------------
    _save_daily_artifacts(iso_date, df_v40, msg, simple_msg)

    # --------------------------------------------------------
    # FASE 3 — Envío Telegram
    # --------------------------------------------------------
    if not no_telegram:
        if entry_msg:
            print("[V4] Enviando entradas…")
            send_telegram_message(entry_msg)

        if exit_msg:
            print("[V4] Enviando salidas…")
            send_telegram_message(exit_msg)

        if portfolio_msg:
            print("[V4] Enviando estado cartera…")
            send_telegram_message(portfolio_msg)

        if not entry_msg and not exit_msg and not portfolio_msg:
            print("[V4] Sin cambios operativos para Telegram.")
    else:
        print("[V4] --no-telegram activado.")
        print(msg)
        if entry_msg:
            print(entry_msg)
        if exit_msg:
            print(exit_msg)
        if portfolio_msg:
            print(portfolio_msg)

    print(f"[V4] Ejecución completa ({iso_date}).")


# ============================================================
if __name__ == "__main__":
    run_v40(no_telegram=False)

