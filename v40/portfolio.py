from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from v40.config_v40 import DATA_DIR
from v40.operability import DEFAULT_BASELINE_COOLDOWN_DAYS, DEFAULT_BASELINE_MAX_CONCURRENT, DEFAULT_SETUP_CAPS, VALID_SETUPS
from v40.risk_backtest import evaluate_trade_lifecycle

PORTFOLIO_PATH = DATA_DIR / 'portfolio_v40.csv'

PORTFOLIO_COLUMNS = [
    'ticker',
    'setup_code',
    'signal_date',
    'entry_price',
    'stop_price',
    'target_price',
    'holding_horizon_days',
    'signal_score',
    'quality_tier',
    'trade_style',
    'status',
    'opened_at',
    'planned_exit_date',
    'closed_at',
    'exit_reason',
    'exit_price',
    'pnl_pct',
]


def load_portfolio() -> pd.DataFrame:
    if not PORTFOLIO_PATH.exists():
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

    df = pd.read_csv(PORTFOLIO_PATH)
    for col in ['signal_date', 'opened_at', 'planned_exit_date', 'closed_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df


def save_portfolio(df: pd.DataFrame) -> None:
    out = df.copy()
    for col in ['signal_date', 'opened_at', 'planned_exit_date', 'closed_at']:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors='coerce')
    out.to_csv(PORTFOLIO_PATH, index=False)


def _open_positions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return df[df['status'] == 'open'].copy()


def _cooldown_ok(portfolio: pd.DataFrame, ticker: str, signal_date: pd.Timestamp, cooldown_days: int) -> bool:
    past = portfolio[(portfolio['ticker'] == ticker) & (portfolio['status'] == 'closed')].copy()
    if past.empty or cooldown_days <= 0:
        return True
    last_closed = pd.to_datetime(past['closed_at'], errors='coerce').dropna()
    if last_closed.empty:
        return True
    return (signal_date - last_closed.max()).days >= cooldown_days


def select_entries(
    signals: pd.DataFrame,
    portfolio: pd.DataFrame,
    max_concurrent: int = DEFAULT_BASELINE_MAX_CONCURRENT,
    cooldown_days: int = DEFAULT_BASELINE_COOLDOWN_DAYS,
    setup_caps: dict[str, int] | None = None,
) -> pd.DataFrame:
    if signals is None or signals.empty:
        return pd.DataFrame(columns=signals.columns if signals is not None else [])

    setup_caps = setup_caps or DEFAULT_SETUP_CAPS
    candidates = signals.copy()
    candidates['signal_date'] = pd.to_datetime(candidates['signal_date'], errors='coerce')
    candidates = candidates[candidates['setup_code'].isin(VALID_SETUPS)]
    candidates = candidates[candidates.get('signal_status', 'new') != 'disabled']
    candidates = candidates.sort_values(['signal_date', 'signal_score', 'ticker'], ascending=[True, False, True]).reset_index(drop=True)

    open_positions = _open_positions(portfolio)
    selected_rows: list[pd.Series] = []

    for _, row in candidates.iterrows():
        ticker = str(row['ticker'])
        setup_code = str(row['setup_code'])
        signal_date = pd.to_datetime(row['signal_date'])

        open_positions = open_positions[pd.to_datetime(open_positions['planned_exit_date'], errors='coerce') >= signal_date].copy()

        if len(open_positions) >= max_concurrent:
            continue
        if (open_positions['ticker'] == ticker).any():
            continue
        if not _cooldown_ok(portfolio, ticker, signal_date, cooldown_days):
            continue

        setup_open = int((open_positions['setup_code'] == setup_code).sum())
        if setup_open >= int(setup_caps.get(setup_code, max_concurrent)):
            continue

        selected_rows.append(row)

        planned_exit_date = signal_date + pd.Timedelta(days=int(row.get('holding_horizon_days', 0) or 0))
        open_positions = pd.concat([
            open_positions,
            pd.DataFrame([{
                'ticker': ticker,
                'setup_code': setup_code,
                'planned_exit_date': planned_exit_date,
                'status': 'open',
            }])
        ], ignore_index=True)

    if not selected_rows:
        return candidates.iloc[0:0].copy()
    return pd.DataFrame(selected_rows).reset_index(drop=True)


def generate_entry_records(selected_signals: pd.DataFrame) -> pd.DataFrame:
    if selected_signals is None or selected_signals.empty:
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

    rows: list[dict[str, Any]] = []
    for _, row in selected_signals.iterrows():
        signal_date = pd.to_datetime(row['signal_date'], errors='coerce')
        horizon = int(row.get('holding_horizon_days', 0) or 0)
        rows.append({
            'ticker': row['ticker'],
            'setup_code': row['setup_code'],
            'signal_date': signal_date,
            'entry_price': row.get('entry_price'),
            'stop_price': row.get('stop_price'),
            'target_price': row.get('target_price'),
            'holding_horizon_days': horizon,
            'signal_score': row.get('signal_score'),
            'quality_tier': row.get('quality_tier'),
            'trade_style': row.get('trade_style'),
            'status': 'open',
            'opened_at': signal_date,
            'planned_exit_date': signal_date + pd.Timedelta(days=horizon),
            'closed_at': pd.NaT,
            'exit_reason': '',
            'exit_price': None,
            'pnl_pct': None,
        })
    return pd.DataFrame(rows, columns=PORTFOLIO_COLUMNS)


def close_positions_with_market_data(portfolio: pd.DataFrame, as_of: pd.Timestamp | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if portfolio.empty:
        return portfolio.copy(), portfolio.iloc[0:0].copy()

    out = portfolio.copy()
    open_mask = out['status'] == 'open'
    if as_of is not None:
        open_mask &= pd.to_datetime(out['planned_exit_date'], errors='coerce') <= pd.to_datetime(as_of)

    candidates = out[open_mask].copy()
    closed_rows = []
    for idx, row in candidates.iterrows():
        lifecycle = evaluate_trade_lifecycle(pd.Series(row))
        if not lifecycle:
            continue
        out.at[idx, 'status'] = 'closed'
        out.at[idx, 'closed_at'] = lifecycle['exit_date']
        out.at[idx, 'exit_reason'] = lifecycle['exit_reason']
        out.at[idx, 'exit_price'] = lifecycle['exit_price']
        out.at[idx, 'pnl_pct'] = float(lifecycle['return_pct']) * 100
        closed_rows.append(out.loc[idx].to_dict())

    return out, pd.DataFrame(closed_rows)
