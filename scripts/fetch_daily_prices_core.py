"""
Core Daily Prices Fetcher for Cobra v4.0
----------------------------------------

Reutiliza la lógica del core v3.x, pero adaptado a:

- Nueva estructura cobra_monkey_v40
- Paths correctos (data/universe_live.txt y outputs/daily_prices/)
- Interfaz estándar requerida por v4.0:

    def run_daily_prices(years: int = 2):
        return (n_total, n_ok, failed, max_date)

Output:
    Guarda ficheros OHLCV diarios en:
        outputs/daily_prices/<TICKER>.csv
"""

from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

import pandas as pd
import yfinance as yf


# ============================================================
# Paths del nuevo proyecto cobra_monkey_v40
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

UNIVERSE_FILE = ROOT / "data" / "universe_live.txt"
OUTPUT_DIR = ROOT / "outputs" / "daily_prices"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Utilidades
# ============================================================

def load_universe() -> List[str]:
    """Carga la lista de tickers desde data/universe_live.txt"""
    if UNIVERSE_FILE.exists():
        with UNIVERSE_FILE.open("r") as f:
            return [line.strip().upper() for line in f if line.strip()]
    print(f"[ERROR] No existe archivo universo: {UNIVERSE_FILE}")
    return []


def fetch_history_yf(symbol: str, years: int = 2) -> pd.DataFrame | None:
    """
    Descarga datos OHLCV con yfinance (2 años por defecto).
    Añadimos fix:
    - threads=False para evitar errores internos de yfinance
    - try/except extendido
    """
    try:
        df = yf.download(
            tickers=str(symbol),
            period=f"{years}y",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,   # ← FIX CLAVE
        )

        # Cuando Yahoo falla, YF puede devolver:
        # None, tuple, dict vacío, o DataFrame sin columnas
        if df is None or not isinstance(df, pd.DataFrame):
            print(f"[WARN] Respuesta inválida para {symbol}")
            return None

        if df.empty:
            print(f"[WARN] Sin datos para {symbol}")
            return None

        # Normalizar multi-index (caso acciones USA)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Validar OHLCV mínimo
        required_cols = {"Open", "High", "Low", "Close"}
        if not required_cols.issubset(set(df.columns)):
            print(f"[WARN] Faltan columnas OHLCV en {symbol}")
            return None

        df.index.name = "date"
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        return df

    except Exception as e:
        print(f"[ERROR] Fallo descargando {symbol}: {e}")
        return None


def save_daily(symbol: str, df: pd.DataFrame):
    """Guarda el CSV diario."""
    out_path = OUTPUT_DIR / f"{symbol}.csv"
    df.to_csv(out_path, index=False)
    return out_path


# ============================================================
# FUNCIÓN PRINCIPAL (interface estándar v4.0)
# ============================================================

def run_daily_prices(years: int = 2) -> Tuple[int, int, List[str], str]:
    """
    Ejecuta Daily Prices completo para todo el universo.

    Retorna:
      n_total  → nº total de tickers del universo
      n_ok     → nº de tickers que descargan correctamente
      failed   → lista de tickers fallidos
      max_date → última fecha disponible (YYYY-MM-DD, o "N/A")

    Compatible con el motor v4.0.
    """
    universe = load_universe()

    if not universe:
        print("[ERROR] Universo vacío.")
        return 0, 0, [], "N/A"

    n_total = len(universe)
    n_ok = 0
    failed: List[str] = []
    max_date = None

    print(f"[INFO] Descargando precios diarios para {n_total} símbolos...")

    for sym in universe:
        df = fetch_history_yf(sym, years=years)

        if df is None or df.empty:
            failed.append(sym)
            continue

        try:
            out = save_daily(sym, df)
            n_ok += 1

            # Actualizar última fecha disponible
            last_date = df["date"].max()
            if max_date is None or last_date > max_date:
                max_date = last_date

            print(f"[OK] {sym}: {out}")
        except Exception as e:
            print(f"[ERROR] Error guardando {sym}: {e}")
            failed.append(sym)

    max_date_str = max_date.strftime("%Y-%m-%d") if max_date is not None else "N/A"

    print(
        f"[DONE] Daily prices → total={n_total}, ok={n_ok}, "
        f"fallidos={len(failed)}, max_date={max_date_str}"
    )

    return n_total, n_ok, failed, max_date_str


# ============================================================
# Ejecución directa
# ============================================================

if __name__ == "__main__":
    run_daily_prices()

