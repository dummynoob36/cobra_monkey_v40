from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from v40.config_v40 import DAILY_PRICES_DIR


@dataclass(frozen=True)
class BacktestResult:
    setup_code: str
    trades: int
    win_rate: float
    avg_return_pct: float
    total_return_pct: float
    final_bank: float
    max_drawdown_pct: float


def _load_ohlc(ticker: str) -> pd.DataFrame | None:
    path = DAILY_PRICES_DIR / f"{ticker}.csv"
    if not path.exists():
        return None

    df = pd.read_csv(path)
    required = {'date', 'high', 'low', 'close'}
    if not required.issubset(df.columns):
        return None

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date', 'high', 'low', 'close']).copy()
    if df.empty:
        return None

    return df.sort_values('date').reset_index(drop=True)


def evaluate_trade(row: pd.Series) -> float | None:
    ticker = str(row.get('ticker', ''))
    signal_date = pd.to_datetime(row.get('signal_date'), errors='coerce')
    entry = row.get('entry_price')
    stop = row.get('stop_price')
    target = row.get('target_price')
    horizon = row.get('holding_horizon_days')

    if pd.isna(signal_date) or pd.isna(entry) or pd.isna(stop) or pd.isna(target) or pd.isna(horizon):
        return None

    df = _load_ohlc(ticker)
    if df is None or df.empty:
        return None

    after = df[df['date'] > signal_date].head(int(horizon))
    if after.empty:
        return None

    for _, bar in after.iterrows():
        low = float(bar['low'])
        high = float(bar['high'])
        close = float(bar['close'])

        if low <= float(stop):
            return (float(stop) / float(entry)) - 1
        if high >= float(target):
            return (float(target) / float(entry)) - 1

    final_close = float(after.iloc[-1]['close'])
    return (final_close / float(entry)) - 1


def backtest_bank(
    df: pd.DataFrame,
    setup_codes: Iterable[str] | None = None,
    initial_bank: float = 1000.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    data = df.copy()
    data['signal_date'] = pd.to_datetime(data['signal_date'], errors='coerce')
    data = data.dropna(subset=['signal_date'])

    if setup_codes is not None:
        setup_codes = set(setup_codes)
        data = data[data['setup_code'].isin(setup_codes)]

    data = data[data.get('signal_status', 'new') != 'disabled']
    data = data.sort_values(['setup_code', 'signal_date', 'ticker']).reset_index(drop=True)
    data['trade_return'] = data.apply(evaluate_trade, axis=1)
    trades = data.dropna(subset=['trade_return']).copy()
    if trades.empty:
        return trades, pd.DataFrame()

    summary_rows = []
    for setup_code, grp in trades.groupby('setup_code'):
        bank = initial_bank
        peak = initial_bank
        max_dd = 0.0

        for r in grp['trade_return']:
            bank *= (1 + float(r))
            peak = max(peak, bank)
            dd = (bank / peak) - 1
            max_dd = min(max_dd, dd)

        summary_rows.append({
            'setup_code': str(setup_code),
            'trades': int(len(grp)),
            'win_rate': round(float((grp['trade_return'] > 0).mean()) * 100, 2),
            'avg_return_pct': round(float(grp['trade_return'].mean()) * 100, 4),
            'total_return_pct': round(((bank / initial_bank) - 1) * 100, 4),
            'final_bank': round(bank, 2),
            'max_drawdown_pct': round(max_dd * 100, 4),
        })

    summary = pd.DataFrame(summary_rows).sort_values('final_bank', ascending=False).reset_index(drop=True)
    return trades, summary
