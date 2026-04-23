from __future__ import annotations

from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd

from v40.config_v40 import DAILY_PRICES_DIR
from v40.engine.build_dataset_v40 import (
    _load_daily_prices,
    _compute_features,
    _flag_A,
    _flag_B,
    _flag_D,
    _flag_E,
    _classify_family,
    _compute_trend_regime_row,
    _detect_eprime_and_super,
    _is_change_candidate,
)
from v40.pattern_quality import classify_signal_quality, market_bucket_for_ticker
from v40.signal_scoring import compute_signal_score
from v40.setup_definitions import derive_setup, derive_trade_plan
from v40.operability import VALID_SETUPS


def build_research_dataset_v40(max_rows_per_ticker: int | None = None) -> pd.DataFrame:
    records = []
    tickers = sorted(f.stem for f in DAILY_PRICES_DIR.glob('*.csv'))

    for ticker in tickers:
        dfp = _load_daily_prices(ticker)
        if dfp is None or dfp.empty:
            continue

        df_feat = _compute_features(dfp)
        if max_rows_per_ticker is not None:
            df_feat = df_feat.tail(max_rows_per_ticker)

        for _, row in df_feat.iterrows():
            signal_date = row.get('date')
            if pd.isna(signal_date):
                continue

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
                'ticker': ticker,
                'pattern_family': fam,
                'trend_regime': regime,
            }))

            base_signal = pd.Series({
                'ticker': ticker,
                'pattern_family': fam,
                'trend_regime': regime,
                'quality_tier': quality_tier,
                'market_bucket': market_bucket,
                'rsi14': float(row.get('rsi14', np.nan)),
                'dist_ema20_atr': float(row.get('dist_ema20_atr', np.nan)),
                'bb_width': float(row.get('bb_width', np.nan)),
                'atr14': float(row.get('atr14', np.nan)),
                'close': float(row.get('close', np.nan)),
            })

            signal_score, signal_score_reasons = compute_signal_score(base_signal)
            setup_code, setup_note, holding_horizon_days = derive_setup(base_signal)
            trade_style, entry_price, stop_price, target_price = derive_trade_plan(base_signal)

            signal_status = 'research' if setup_code in VALID_SETUPS else 'disabled'

            records.append({
                'ticker': ticker,
                'signal_date': pd.to_datetime(signal_date).isoformat(),
                'system': 'v40_research',
                'pattern_family': fam,
                'A_sobreventa_estructural': A,
                'B_rebote_suave': B,
                'D_pullback_controlado': D,
                'E_microcorreccion_compresion': E,
                'close': float(row.get('close', np.nan)),
                'rsi14': float(row.get('rsi14', np.nan)),
                'atr14': float(row.get('atr14', np.nan)),
                'dist_ema20_atr': float(row.get('dist_ema20_atr', np.nan)),
                'dist_bb_lo_atr': float(row.get('dist_bb_lo_atr', np.nan)),
                'body_atr_ratio': float(row.get('body_atr_ratio', np.nan)),
                'wick_low_atr_ratio': float(row.get('wick_low_atr_ratio', np.nan)),
                'bb_width': float(row.get('bb_width', np.nan)),
                'dist_ema20_pct': float(row.get('dist_ema20_pct', np.nan)),
                'dist_ema50_pct': float(row.get('dist_ema50_pct', np.nan)),
                'roc10': float(row.get('roc10', np.nan)),
                'vol_zscore10': float(row.get('vol_zscore10', np.nan)),
                'trend_regime': regime,
                'market_bucket': market_bucket,
                'is_trend_up': up,
                'is_trend_down': down,
                'is_trend_range': rng,
                'is_supersignal_v40': is_super,
                'supersignal_tipo_v40': super_type if is_super else '',
                'is_e_prime_v40': is_eprime,
                'is_change_candidate': is_change,
                'quality_tier': quality_tier,
                'quality_note': quality_note,
                'signal_score': signal_score,
                'signal_score_reasons': signal_score_reasons,
                'setup_code': setup_code,
                'setup_note': setup_note,
                'holding_horizon_days': holding_horizon_days,
                'trade_style': trade_style,
                'entry_price': entry_price,
                'stop_price': stop_price,
                'target_price': target_price,
                'signal_status': signal_status,
            })

    out = pd.DataFrame(records)
    if out.empty:
        return out

    out['signal_date'] = pd.to_datetime(out['signal_date'], errors='coerce')
    out = out.dropna(subset=['signal_date']).sort_values(['signal_date', 'ticker']).reset_index(drop=True)
    return out
