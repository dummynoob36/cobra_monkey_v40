"""
FASE 0 — Wrapper de Daily Prices para Cobra v4.0
------------------------------------------------

Este módulo ejecuta la actualización de precios diarios delegando en el
core de v3.x (scripts/fetch_daily_prices_core.py), pero añade:

- Manejo robusto de errores
- Logs consistentes para el motor v4.0
- Retorno estándar para FASE 0 del engine
"""

from __future__ import annotations
from typing import List, Tuple

from v40.config_v40 import DEFAULT_HISTORY_YEARS
from scripts.fetch_daily_prices_core import run_daily_prices


def run_daily_prices_v40(years: int = DEFAULT_HISTORY_YEARS) -> Tuple[int, int, List[str], str]:
    """
    Ejecuta la FASE 0 del motor v4.0:

        1. Actualiza daily prices para todo el universo
        2. Devuelve métricas estándar para reporting
        3. Maneja errores sin interrumpir el motor

    Parámetros
    ----------
    years : int
        Número de años de histórico a garantizar.

    Retorno
    -------
    (n_total, n_ok, failed, max_date)
    """

    print(f"[V4][FASE 0] Iniciando actualización de Daily Prices ({years} años)…")

    try:
        n_total, n_ok, failed, max_date = run_daily_prices(years=years)

    except Exception as e:
        print(f"[V4][FASE 0][ERROR] Fallo crítico ejecutando daily prices: {e}")
        print("[V4][FASE 0] Se devuelve estado vacío.")
        return 0, 0, [], "N/A"

    print(
        f"[V4][FASE 0] COMPLETADO → universo={n_total}, ok={n_ok}, "
        f"fallidos={len(failed)}, max_date={max_date}"
    )

    if failed:
        print("[V4][FASE 0][WARN] Tickers con error:")
        for t in failed:
            print(f"  - {t}")

    return n_total, n_ok, failed, max_date

