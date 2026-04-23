from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from v40.config_v40 import DAILY_PRICES_DIR


class PatternValidationDataError(RuntimeError):
    """Se lanza cuando faltan datos mínimos para validar patrones con precios forward."""

DEFAULT_FORWARD_DAYS: tuple[int, ...] = (1, 3, 5, 10, 20)


@dataclass(frozen=True)
class ValidationSummary:
    pattern_family: str
    signals: int
    unique_tickers: int
    hit_rate_5d: float | None
    avg_return_5d: float | None
    median_return_5d: float | None
    avg_return_10d: float | None
    avg_return_20d: float | None


def _safe_float(value) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), 4)


def _load_price_series(ticker: str) -> pd.DataFrame | None:
    csv_path = DAILY_PRICES_DIR / f"{ticker}.csv"
    if not csv_path.exists():
        return None

    df = pd.read_csv(csv_path)
    if "date" not in df.columns or "close" not in df.columns:
        return None

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "close"]).copy()
    if df.empty:
        return None

    df = df.sort_values("date")[["date", "close"]].drop_duplicates(subset=["date"], keep="last")
    return df.reset_index(drop=True)


def enrich_dataset_with_forward_returns(
    df_dataset: pd.DataFrame,
    forward_days: Iterable[int] = DEFAULT_FORWARD_DAYS,
) -> pd.DataFrame:
    """
    Añade retornos forward por ticker/fecha de señal usando los CSV de daily prices.
    No modifica el dataframe original.
    """
    if df_dataset is None or df_dataset.empty:
        return pd.DataFrame()

    df = df_dataset.copy()
    df["signal_date"] = pd.to_datetime(df["signal_date"], errors="coerce")
    df = df.dropna(subset=["signal_date", "ticker"]).copy()
    if df.empty:
        return df

    forward_days = tuple(sorted({int(x) for x in forward_days if int(x) > 0}))
    if not forward_days:
        return df

    for horizon in forward_days:
        df[f"ret_{horizon}d"] = pd.NA

    matched_any_price = False

    for ticker, idx in df.groupby("ticker").groups.items():
        px = _load_price_series(str(ticker))
        if px is None or px.empty:
            continue

        px = px.copy()
        px["entry_close"] = px["close"]

        for horizon in forward_days:
            px[f"future_close_{horizon}d"] = px["close"].shift(-horizon)
            px[f"ret_{horizon}d"] = (px[f"future_close_{horizon}d"] / px["entry_close"]) - 1

        merged = df.loc[idx, ["signal_date"]].merge(
            px[["date"] + [f"ret_{h}d" for h in forward_days]],
            left_on="signal_date",
            right_on="date",
            how="left",
        )

        if merged[[f"ret_{h}d" for h in forward_days]].notna().any().any():
            matched_any_price = True

        for horizon in forward_days:
            df.loc[idx, f"ret_{horizon}d"] = merged[f"ret_{horizon}d"].values

    if not matched_any_price:
        raise PatternValidationDataError(
            "No se pudieron alinear señales con precios forward. "
            "Faltan CSVs en outputs/daily_prices o no contienen las fechas del dataset."
        )

    return df


def summarize_pattern_validation(
    df_dataset: pd.DataFrame,
    forward_days: Iterable[int] = DEFAULT_FORWARD_DAYS,
) -> pd.DataFrame:
    """
    Resume la calidad histórica observable por patrón a distintos horizontes.
    Sirve para tratar cada patrón como hipótesis testable, no como axioma.
    """
    df = df_dataset.copy()
    required_return_cols = [f"ret_{int(h)}d" for h in forward_days if int(h) > 0]
    has_precomputed_returns = bool(required_return_cols) and all(col in df.columns for col in required_return_cols)

    if not has_precomputed_returns:
        df = enrich_dataset_with_forward_returns(df, forward_days=forward_days)
    if df.empty or "pattern_family" not in df.columns:
        return pd.DataFrame()

    rows: list[ValidationSummary] = []

    for pattern, grp in df.groupby("pattern_family", dropna=False):
        ret_5 = pd.to_numeric(grp.get("ret_5d"), errors="coerce") if "ret_5d" in grp else pd.Series(dtype=float)
        ret_10 = pd.to_numeric(grp.get("ret_10d"), errors="coerce") if "ret_10d" in grp else pd.Series(dtype=float)
        ret_20 = pd.to_numeric(grp.get("ret_20d"), errors="coerce") if "ret_20d" in grp else pd.Series(dtype=float)

        hit_rate_5d = None
        if not ret_5.empty and ret_5.notna().any():
            hit_rate_5d = round(float((ret_5 > 0).mean()) * 100, 2)

        rows.append(
            ValidationSummary(
                pattern_family=str(pattern),
                signals=int(len(grp)),
                unique_tickers=int(grp["ticker"].nunique()) if "ticker" in grp else 0,
                hit_rate_5d=hit_rate_5d,
                avg_return_5d=_safe_float(ret_5.mean() * 100) if not ret_5.empty else None,
                median_return_5d=_safe_float(ret_5.median() * 100) if not ret_5.empty else None,
                avg_return_10d=_safe_float(ret_10.mean() * 100) if not ret_10.empty else None,
                avg_return_20d=_safe_float(ret_20.mean() * 100) if not ret_20.empty else None,
            )
        )

    out = pd.DataFrame([r.__dict__ for r in rows])
    if out.empty:
        return out

    return out.sort_values(["avg_return_5d", "signals"], ascending=[False, False], na_position="last").reset_index(drop=True)


def build_pattern_validation_report(
    df_dataset: pd.DataFrame,
    forward_days: Iterable[int] = DEFAULT_FORWARD_DAYS,
    top_n: int = 12,
) -> str:
    try:
        summary = summarize_pattern_validation(df_dataset, forward_days=forward_days)
    except PatternValidationDataError as exc:
        return f"📐 Validación de patrones\n{exc}"

    if summary.empty:
        return "📐 Validación de patrones\nNo hay datos suficientes para validar patrones todavía."

    lines = ["📐 Validación de patrones (hipótesis, no dogma)", ""]
    for _, row in summary.head(top_n).iterrows():
        lines.append(
            (
                f"• {row['pattern_family']}: "
                f"n={int(row['signals'])}, "
                f"tickers={int(row['unique_tickers'])}, "
                f"hit5={row['hit_rate_5d'] if pd.notna(row['hit_rate_5d']) else 'N/A'}%, "
                f"avg5={row['avg_return_5d'] if pd.notna(row['avg_return_5d']) else 'N/A'}%, "
                f"med5={row['median_return_5d'] if pd.notna(row['median_return_5d']) else 'N/A'}%, "
                f"avg10={row['avg_return_10d'] if pd.notna(row['avg_return_10d']) else 'N/A'}%, "
                f"avg20={row['avg_return_20d'] if pd.notna(row['avg_return_20d']) else 'N/A'}%"
            )
        )

    lines.append("")
    lines.append("Nota: esto todavía no sustituye un backtest serio con costes, slippage y walk-forward.")
    return "\n".join(lines)
