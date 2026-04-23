from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from v40.config_v40 import (
    DAILY_PRICES_DIR,
    DATASET_V40_PATH,
    DATA_DIR,
)
from v40.pattern_definitions import flag_pattern
from v40.pattern_quality import classify_signal_quality, market_bucket_for_ticker
from v40.signal_scoring import compute_signal_score
from v40.setup_definitions import derive_setup, derive_trade_plan
from v40.operability import VALID_SETUPS

# =============================================================================
# UTILIDADES FECHA
# =============================================================================

def _today() -> date:
    return datetime.utcnow().date()


# =============================================================================
# CARGA DE PRECIOS
# =============================================================================

def _load_daily_prices(ticker: str) -> pd.DataFrame | None:
    path = DAILY_PRICES_DIR / f"{ticker}.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)

    # Buscar columna fecha
    date_col = None
    if "date" in df.columns:
        date_col = "date"
    else:
        candidates = [c for c in df.columns if c.lower().startswith("date")]
        if candidates:
            date_col = candidates[0]

    if not date_col:
        return None

    # Fechas limpias
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])
    df = df.rename(columns={date_col: "date"})
    df["date"] = df["date"].dt.date
    orig_dates = df["date"].copy()

    # --- FIX DEFINITIVO COLUMNAS DUPLICADAS ---
    from collections import defaultdict
    groups = defaultdict(list)

    for col in df.columns:
        base = col.split(".")[0].lower()
        groups[base].append(col)

    cleaned = {"date": orig_dates}

    for base in ["open", "high", "low", "close", "volume"]:
        cols = groups.get(base, [])
        if not cols:
            cleaned[base] = pd.Series([np.nan] * len(df))
            continue

        series = df[cols[0]]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]

        cleaned[base] = series

    df_clean = pd.DataFrame(cleaned)

    if df_clean["close"].isna().all():
        return None

    return df_clean.sort_values("date").reset_index(drop=True)


# =============================================================================
# INDICADORES
# =============================================================================

def _ema(x: pd.Series, span: int) -> pd.Series:
    return x.ewm(span=span, adjust=False).mean()


def _rsi(x: pd.Series, period: int = 14) -> pd.Series:
    diff = x.diff()
    gain = diff.clip(lower=0)
    loss = -diff.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(alpha=1 / period, adjust=False).mean()


def _compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    close = df["close"]
    open_ = df.get("open", close)
    high = df.get("high", close)
    low = df.get("low", close)
    vol = df.get("volume", pd.Series(index=df.index, dtype=float))

    ema20 = _ema(close, 20)
    ema50 = _ema(close, 50)
    atr14 = _atr(pd.DataFrame({"high": high, "low": low, "close": close}), 14)
    rsi14 = _rsi(close)

    roc10 = (close / close.shift(10) - 1) * 100

    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std(ddof=0)
    bb_up = ma20 + 2 * std20
    bb_lo = ma20 - 2 * std20
    bb_width = (bb_up - bb_lo) / atr14

    df["dist_ema20_atr"] = (close - ema20) / atr14
    df["dist_bb_lo_atr"] = (close - bb_lo) / atr14
    df["body_atr_ratio"] = (close - open_) / atr14
    df["wick_low_atr_ratio"] = (open_.where(open_ < close, close) - low) / atr14
    df["bb_width"] = bb_width

    df["dist_ema20_pct"] = (close / ema20 - 1) * 100
    df["dist_ema50_pct"] = (close / ema50 - 1) * 100

    df["rsi14"] = rsi14
    df["atr14"] = atr14
    df["roc10"] = roc10

    vol_ma10 = vol.rolling(10).mean()
    vol_std10 = vol.rolling(10).std(ddof=0)
    df["vol_zscore10"] = (vol - vol_ma10) / vol_std10.replace(0, np.nan)

    return df


# =============================================================================
# TENDENCIA
# =============================================================================

def _compute_trend_regime_row(row):
    ema20 = row.get("dist_ema20_pct", np.nan)
    ema50 = row.get("dist_ema50_pct", np.nan)
    roc10 = row.get("roc10", np.nan)

    score = 0
    score += 1 if ema20 > 0 else -1 if ema20 < 0 else 0
    score += 1 if ema50 > 0 else -1 if ema50 < 0 else 0
    score += 1 if roc10 > 0 else -1 if roc10 < 0 else 0

    if score >= 2:
        regime = "UP"
    elif score <= -2:
        regime = "DOWN"
    else:
        regime = "RANGE"

    return regime, regime == "UP", regime == "DOWN", regime == "RANGE"


# =============================================================================
# PATRONES A / B / D / E
# =============================================================================

def _flag_A(r):
    return flag_pattern(r, "A")


def _flag_B(r):
    return flag_pattern(r, "B")


def _flag_D(r):
    return flag_pattern(r, "D")


def _flag_E(r):
    return flag_pattern(r, "E")


def _classify_family(a, b, d, e):
    chosen = []
    if a:
        chosen.append("A")
    if b:
        chosen.append("B")
    if d:
        chosen.append("D")
    if e:
        chosen.append("E")

    if not chosen:
        return "OTHER"

    order = {"A": 0, "B": 1, "D": 2, "E": 3}
    return "_".join(sorted(chosen, key=lambda x: order[x]))


# =============================================================================
# SUPERSEÑALES / E-PRIME
# =============================================================================

def _detect_eprime_and_super(row, regime, fam):
    rsi14 = float(row.get("rsi14", np.nan))
    dist_bb_lo = float(row.get("dist_bb_lo_atr", np.nan))
    wick_low = float(row.get("wick_low_atr_ratio", np.nan))
    dist_ema20 = float(row.get("dist_ema20_atr", np.nan))
    body = float(row.get("body_atr_ratio", np.nan))
    bb_width = float(row.get("bb_width", np.nan))

    fam_parts = fam.split("_")

    is_eprime = False
    if "E" in fam_parts and regime == "UP":
        if (
            45 <= rsi14 <= 65
            and -0.2 <= dist_ema20 <= 0.8
            and 0.2 <= body <= 1.2
            and (bb_width <= 1.0 or abs(dist_bb_lo) <= 0.6)
        ):
            is_eprime = True

    is_super = False
    super_type = ""

    if "A" in fam_parts:
        if rsi14 <= 32 and dist_bb_lo <= -1.2 and wick_low >= 0.4:
            is_super = True
            super_type = "REV_A_PROF"

    if not is_super and "D" in fam_parts and regime == "UP":
        if -1 <= dist_ema20 <= 0.5 and 0.2 <= body <= 1.0:
            is_super = True
            super_type = "PULLBACK_TREND_D"

    if not is_super and "E" in fam_parts and regime == "UP":
        if bb_width < 1.0 or abs(dist_bb_lo) < 0.8:
            is_super = True
            super_type = "COMPRESSION_E_BREAKOUT"

    if is_eprime:
        is_super = True
        super_type = "E_PRIME"

    return is_eprime, is_super, super_type


# =============================================================================
# CAMBIO DE TENDENCIA
# =============================================================================

def _is_change_candidate(row, regime, fam):
    if "A" not in fam or regime != "DOWN":
        return False

    rsi14 = float(row.get("rsi14", np.nan))
    dist_ema20 = float(row.get("dist_ema20_atr", np.nan))

    return rsi14 < 30 and dist_ema20 < -1.0


# =============================================================================
# CONSTRUCCIÓN DATASET V40 (ACUMULATIVO)
# =============================================================================

def build_dataset_v40() -> Tuple[pd.DataFrame, date]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    analysis_date = _today()

    # Cargar dataset previo
    if DATASET_V40_PATH.exists():
        df_prev = pd.read_csv(DATASET_V40_PATH)
        df_prev["signal_date"] = pd.to_datetime(df_prev["signal_date"], errors="coerce")
        df_prev = df_prev.dropna(subset=["signal_date"])
    else:
        df_prev = pd.DataFrame()

    # Evitar duplicar señales del mismo día de ejecución
    if not df_prev.empty:
        df_prev = df_prev[df_prev["signal_date"].dt.date != analysis_date]

    tickers = sorted(f.stem for f in DAILY_PRICES_DIR.glob("*.csv"))

    records = []
    example_printed = False

    for ticker in tickers:
        dfp = _load_daily_prices(ticker)
        if dfp is None or dfp.empty:
            continue

        dates_set = set(dfp["date"])
        last_date = max(dates_set)

        if analysis_date in dates_set:
            use_date = analysis_date
        else:
            use_date = last_date
            if not example_printed:
                print(
                    f"[V4][INFO] No hay vela para {analysis_date}. "
                    f"Usando última {last_date} (ejemplo: {ticker})"
                )
                example_printed = True

        df_cut = dfp[dfp["date"] <= use_date].tail(120)
        if df_cut.empty:
            continue

        df_feat = _compute_features(df_cut)
        row_today = df_feat[df_feat["date"] == use_date]
        if row_today.empty:
            continue

        row = row_today.iloc[0]

        A = _flag_A(row)
        B = _flag_B(row)
        D = _flag_D(row)
        E = _flag_E(row)

        if not any([A, B, D, E]):
            continue

        regime, up, down, rng = _compute_trend_regime_row(row)
        fam = _classify_family(A, B, D, E)

        is_eprime, is_super, super_type = _detect_eprime_and_super(row, regime, fam)
        is_change = _is_change_candidate(row, regime, fam)

        market_bucket = market_bucket_for_ticker(ticker)
        quality_tier, quality_note = classify_signal_quality(pd.Series({
            "ticker": ticker,
            "pattern_family": fam,
            "trend_regime": regime,
        }))
        base_signal = pd.Series({
            "ticker": ticker,
            "pattern_family": fam,
            "trend_regime": regime,
            "quality_tier": quality_tier,
            "market_bucket": market_bucket,
            "rsi14": float(row.get("rsi14", np.nan)),
            "dist_ema20_atr": float(row.get("dist_ema20_atr", np.nan)),
            "bb_width": float(row.get("bb_width", np.nan)),
            "atr14": float(row.get("atr14", np.nan)),
            "close": float(row.get("close", np.nan)),
        })
        signal_score, signal_score_reasons = compute_signal_score(base_signal)
        setup_code, setup_note, holding_horizon_days = derive_setup(base_signal)
        trade_style, entry_price, stop_price, target_price = derive_trade_plan(base_signal)

        signal_status = 'new' if setup_code in VALID_SETUPS else 'disabled'

        rec = {
            "ticker": ticker,
            "signal_date": analysis_date.isoformat(),
            "system": "v40",
            "pattern_family": fam,
            "A_sobreventa_estructural": A,
            "B_rebote_suave": B,
            "D_pullback_controlado": D,
            "E_microcorreccion_compresion": E,
            "rsi14": float(row.get("rsi14", np.nan)),
            "atr14": float(row.get("atr14", np.nan)),
            "dist_ema20_atr": float(row.get("dist_ema20_atr", np.nan)),
            "dist_bb_lo_atr": float(row.get("dist_bb_lo_atr", np.nan)),
            "body_atr_ratio": float(row.get("body_atr_ratio", np.nan)),
            "wick_low_atr_ratio": float(row.get("wick_low_atr_ratio", np.nan)),
            "bb_width": float(row.get("bb_width", np.nan)),
            "dist_ema20_pct": float(row.get("dist_ema20_pct", np.nan)),
            "dist_ema50_pct": float(row.get("dist_ema50_pct", np.nan)),
            "roc10": float(row.get("roc10", np.nan)),
            "vol_zscore10": float(row.get("vol_zscore10", np.nan)),
            "trend_regime": regime,
            "market_bucket": market_bucket,
            "is_trend_up": up,
            "is_trend_down": down,
            "is_trend_range": rng,
            "is_supersignal_v40": is_super,
            "supersignal_tipo_v40": super_type if is_super else "",
            "is_e_prime_v40": is_eprime,
            "is_change_candidate": is_change,
            "quality_tier": quality_tier,
            "quality_note": quality_note,
            "signal_score": signal_score,
            "signal_score_reasons": signal_score_reasons,
            "setup_code": setup_code,
            "setup_note": setup_note,
            "holding_horizon_days": holding_horizon_days,
            "trade_style": trade_style,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": target_price,
            "signal_status": signal_status,
        }

        records.append(rec)

    df_new = pd.DataFrame(records)

    if df_prev.empty:
        df_all = df_new
    elif df_new.empty:
        df_all = df_prev
    else:
        df_all = pd.concat([df_prev, df_new], ignore_index=True)

    if not df_all.empty:
        df_all["signal_date"] = pd.to_datetime(df_all["signal_date"])
        df_all = df_all.sort_values(["signal_date", "ticker"])
        df_all.to_csv(DATASET_V40_PATH, index=False)
        start_date = df_all["signal_date"].dt.date.min()
    else:
        start_date = analysis_date

    print(f"[V4][OK] dataset_v40 guardado ({len(df_all)} filas)")
    return df_all, start_date

