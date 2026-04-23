from __future__ import annotations

import numpy as np

PATTERN_RULES_V40: dict[str, dict[str, object]] = {
    "A": {
        "label": "Sobreventa estructural",
        "hypothesis": "Busca activos con sobreventa fuerte pero cuerpo diario todavía controlado.",
        "conditions": {
            "rsi14": (5, 35),
            "dist_ema20_atr": (-6, -1.8),
            "dist_bb_lo_atr": (-2.5, 1.5),
            "body_atr_ratio_abs_max": 1.6,
        },
    },
    "B": {
        "label": "Rebote suave",
        "hypothesis": "Busca rebotes incipientes sin expansión extrema de volumen o cuerpo.",
        "conditions": {
            "rsi14": (20, 50),
            "dist_ema20_atr": (-3.5, -0.8),
            "dist_bb_lo_atr": (-1, 2.5),
            "body_atr_ratio_abs_max": 1.0,
            "vol_zscore10": (-2, 2),
        },
    },
    "D": {
        "label": "Pullback controlado",
        "hypothesis": "Busca retrocesos moderados con compresión de cuerpo y volumen relativamente neutro.",
        "conditions": {
            "rsi14": (25, 55),
            "dist_ema20_atr": (-2.5, -1),
            "dist_bb_lo_atr": (0, 4.5),
            "body_atr_ratio_abs_max": 0.9,
            "vol_zscore10": (-2, 1.5),
        },
    },
    "E": {
        "label": "Microcorrección / Compresión",
        "hypothesis": "Busca compresiones cerca de estructura con ancho de bandas contenido.",
        "conditions": {
            "dist_ema20_atr": (-1.8, 1.0),
            "dist_bb_lo_atr": (0.5, 6.5),
            "body_atr_ratio_abs_max": 1.0,
            "bb_width_max": 2.5,
            "vol_zscore10": (-2, 1.5),
        },
    },
}


def _in_range(value: float, lower: float, upper: float) -> bool:
    if np.isnan(value):
        return False
    return lower <= value <= upper


def _in_range_or_nan(value: float, lower: float, upper: float) -> bool:
    return np.isnan(value) or lower <= value <= upper


def flag_pattern(row, pattern_key: str) -> bool:
    rules = PATTERN_RULES_V40[pattern_key]["conditions"]

    if pattern_key == "A":
        return (
            _in_range(float(row.get("rsi14", np.nan)), *rules["rsi14"])
            and _in_range(float(row.get("dist_ema20_atr", np.nan)), *rules["dist_ema20_atr"])
            and _in_range(float(row.get("dist_bb_lo_atr", np.nan)), *rules["dist_bb_lo_atr"])
            and abs(float(row.get("body_atr_ratio", np.nan))) <= rules["body_atr_ratio_abs_max"]
        )

    if pattern_key == "B":
        return (
            _in_range(float(row.get("rsi14", np.nan)), *rules["rsi14"])
            and _in_range(float(row.get("dist_ema20_atr", np.nan)), *rules["dist_ema20_atr"])
            and _in_range(float(row.get("dist_bb_lo_atr", np.nan)), *rules["dist_bb_lo_atr"])
            and abs(float(row.get("body_atr_ratio", np.nan))) <= rules["body_atr_ratio_abs_max"]
            and _in_range_or_nan(float(row.get("vol_zscore10", np.nan)), *rules["vol_zscore10"])
        )

    if pattern_key == "D":
        return (
            _in_range(float(row.get("rsi14", np.nan)), *rules["rsi14"])
            and _in_range(float(row.get("dist_ema20_atr", np.nan)), *rules["dist_ema20_atr"])
            and _in_range(float(row.get("dist_bb_lo_atr", np.nan)), *rules["dist_bb_lo_atr"])
            and abs(float(row.get("body_atr_ratio", np.nan))) <= rules["body_atr_ratio_abs_max"]
            and _in_range_or_nan(float(row.get("vol_zscore10", np.nan)), *rules["vol_zscore10"])
        )

    if pattern_key == "E":
        return (
            _in_range(float(row.get("dist_ema20_atr", np.nan)), *rules["dist_ema20_atr"])
            and _in_range(float(row.get("dist_bb_lo_atr", np.nan)), *rules["dist_bb_lo_atr"])
            and abs(float(row.get("body_atr_ratio", np.nan))) <= rules["body_atr_ratio_abs_max"]
            and float(row.get("bb_width", np.nan)) <= rules["bb_width_max"]
            and _in_range_or_nan(float(row.get("vol_zscore10", np.nan)), *rules["vol_zscore10"])
        )

    raise KeyError(f'Patrón no soportado: {pattern_key}')
