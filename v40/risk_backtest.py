from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from v40.config_v40 import DAILY_PRICES_DIR
from v40.operability import DEFAULT_SETUP_CAPS


@dataclass(frozen=True)
class RiskBacktestResult:
    setup_code: str
    trades: int
    win_rate: float
    avg_r_multiple: float
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


def evaluate_trade_lifecycle(row: pd.Series) -> dict[str, object] | None:
    ticker = str(row.get('ticker', ''))
    signal_date = pd.to_datetime(row.get('signal_date'), errors='coerce')
    entry = row.get('entry_price')
    stop = row.get('stop_price')
    target = row.get('target_price')
    horizon = row.get('holding_horizon_days')

    if pd.isna(signal_date) or pd.isna(entry) or pd.isna(stop) or pd.isna(target) or pd.isna(horizon):
        return None

    entry = float(entry)
    stop = float(stop)
    target = float(target)
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return None

    df = _load_ohlc(ticker)
    if df is None or df.empty:
        return None

    after = df[df['date'] > signal_date].head(int(horizon)).copy()
    if after.empty:
        return None

    days_to_stop = None
    days_to_target = None

    for day_idx, (_, bar) in enumerate(after.iterrows(), start=1):
        low = float(bar['low'])
        high = float(bar['high'])
        bar_date = pd.to_datetime(bar['date'])

        if low <= stop:
            days_to_stop = day_idx
            return {
                'exit_reason': 'stop',
                'exit_date': bar_date,
                'days_held': day_idx,
                'days_to_stop': days_to_stop,
                'days_to_target': days_to_target,
                'exit_price': stop,
                'r_multiple': -1.0,
                'return_pct': (stop / entry) - 1,
            }
        if high >= target:
            days_to_target = day_idx
            return {
                'exit_reason': 'target',
                'exit_date': bar_date,
                'days_held': day_idx,
                'days_to_stop': days_to_stop,
                'days_to_target': days_to_target,
                'exit_price': target,
                'r_multiple': (target - entry) / risk_per_share,
                'return_pct': (target / entry) - 1,
            }

    final_bar = after.iloc[-1]
    final_close = float(final_bar['close'])
    return {
        'exit_reason': 'expiry',
        'exit_date': pd.to_datetime(final_bar['date']),
        'days_held': int(len(after)),
        'days_to_stop': days_to_stop,
        'days_to_target': days_to_target,
        'exit_price': final_close,
        'r_multiple': (final_close - entry) / risk_per_share,
        'return_pct': (final_close / entry) - 1,
    }


def _sort_candidates(trades: pd.DataFrame) -> pd.DataFrame:
    score_cols = [c for c in ['signal_score', 'quality_tier', 'setup_code', 'ticker'] if c in trades.columns]
    ascending = []
    for c in score_cols:
        ascending.append(False if c == 'signal_score' else True)
    if not score_cols:
        return trades.sort_values(['signal_date', 'setup_code', 'ticker']).reset_index(drop=True)
    return trades.sort_values(['signal_date', *score_cols], ascending=[True, *ascending]).reset_index(drop=True)


def _apply_operability_constraints(
    trades: pd.DataFrame,
    max_concurrent_positions: int | None = None,
    cooldown_days: int = 0,
    setup_caps: dict[str, int] | None = None,
) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()

    constrained = _sort_candidates(trades)
    accepted_rows: list[pd.Series] = []
    open_positions: list[dict[str, object]] = []
    last_exit_by_ticker: dict[str, pd.Timestamp] = {}
    setup_caps = setup_caps or DEFAULT_SETUP_CAPS

    for _, row in constrained.iterrows():
        signal_date = pd.to_datetime(row['signal_date'])
        ticker = str(row['ticker'])
        setup_code = str(row['setup_code'])
        exit_date = pd.to_datetime(row['exit_date'])

        open_positions = [pos for pos in open_positions if pd.to_datetime(pos['exit_date']) >= signal_date]

        if cooldown_days > 0 and ticker in last_exit_by_ticker:
            days_since_last_exit = (signal_date - last_exit_by_ticker[ticker]).days
            if days_since_last_exit < cooldown_days:
                continue

        if max_concurrent_positions is not None and len(open_positions) >= max_concurrent_positions:
            continue

        setup_open = sum(1 for pos in open_positions if str(pos['setup_code']) == setup_code)
        if setup_caps.get(setup_code) is not None and setup_open >= int(setup_caps[setup_code]):
            continue

        accepted_rows.append(row)
        open_positions.append({'ticker': ticker, 'exit_date': exit_date, 'setup_code': setup_code})
        last_exit_by_ticker[ticker] = exit_date

    if not accepted_rows:
        return constrained.iloc[0:0].copy()

    return pd.DataFrame(accepted_rows).reset_index(drop=True)


def summarize_trade_lifecycle(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    rows = []
    for setup_code, grp in trades.groupby('setup_code'):
        rows.append({
            'setup_code': str(setup_code),
            'trades': int(len(grp)),
            'win_rate': round(float((grp['r_multiple'] > 0).mean()) * 100, 2),
            'avg_r_multiple': round(float(grp['r_multiple'].mean()), 4),
            'avg_return_pct': round(float(grp['return_pct'].mean()) * 100, 4),
            'avg_days_held': round(float(grp['days_held'].mean()), 2),
            'median_days_held': round(float(grp['days_held'].median()), 2),
            'avg_days_to_target': round(float(grp.loc[grp['exit_reason'] == 'target', 'days_held'].mean()), 2)
            if not grp.loc[grp['exit_reason'] == 'target'].empty else None,
            'avg_days_to_stop': round(float(grp.loc[grp['exit_reason'] == 'stop', 'days_held'].mean()), 2)
            if not grp.loc[grp['exit_reason'] == 'stop'].empty else None,
            'expiry_rate_pct': round(float((grp['exit_reason'] == 'expiry').mean()) * 100, 2),
            'target_rate_pct': round(float((grp['exit_reason'] == 'target').mean()) * 100, 2),
            'stop_rate_pct': round(float((grp['exit_reason'] == 'stop').mean()) * 100, 2),
            'avg_concurrent_exposure': round(float(grp['concurrent_positions_at_entry'].mean()), 2)
            if 'concurrent_positions_at_entry' in grp else None,
            'max_concurrent_exposure': int(grp['concurrent_positions_at_entry'].max())
            if 'concurrent_positions_at_entry' in grp and not grp.empty else None,
        })

    return pd.DataFrame(rows).sort_values('avg_r_multiple', ascending=False).reset_index(drop=True)


def backtest_fixed_risk(
    df: pd.DataFrame,
    setup_codes: list[str],
    initial_bank: float = 1000.0,
    risk_fraction: float = 0.01,
    max_concurrent_positions: int | None = None,
    cooldown_days: int = 0,
    setup_caps: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = df.copy()
    data['signal_date'] = pd.to_datetime(data['signal_date'], errors='coerce')
    data = data.dropna(subset=['signal_date'])
    data = data[data['setup_code'].isin(setup_codes)]
    data = data[data.get('signal_status', 'new') != 'disabled']
    data = data.sort_values(['setup_code', 'signal_date', 'ticker']).reset_index(drop=True)

    lifecycle = data.apply(evaluate_trade_lifecycle, axis=1)
    lifecycle_df = pd.DataFrame([item if isinstance(item, dict) else {} for item in lifecycle])
    trades = pd.concat([data.reset_index(drop=True), lifecycle_df], axis=1)
    trades = trades.dropna(subset=['r_multiple', 'exit_date']).copy()
    if trades.empty:
        return trades, pd.DataFrame()

    trades = _apply_operability_constraints(
        trades,
        max_concurrent_positions=max_concurrent_positions,
        cooldown_days=cooldown_days,
        setup_caps=setup_caps,
    )
    if trades.empty:
        return trades, pd.DataFrame()

    constrained_open_positions: list[dict[str, object]] = []
    constrained_concurrency = []
    setup_concurrency = []
    for _, row in trades.iterrows():
        signal_date = pd.to_datetime(row['signal_date'])
        setup_code = str(row['setup_code'])
        constrained_open_positions = [pos for pos in constrained_open_positions if pd.to_datetime(pos['exit_date']) >= signal_date]
        constrained_concurrency.append(len(constrained_open_positions))
        setup_concurrency.append(sum(1 for pos in constrained_open_positions if str(pos['setup_code']) == setup_code))
        constrained_open_positions.append({'exit_date': pd.to_datetime(row['exit_date']), 'setup_code': setup_code})
    trades['concurrent_positions_at_entry'] = constrained_concurrency
    trades['setup_positions_at_entry'] = setup_concurrency

    summaries = []
    for setup_code, grp in trades.groupby('setup_code'):
        bank = initial_bank
        peak = initial_bank
        max_dd = 0.0

        for r in grp['r_multiple']:
            risk_amount = bank * risk_fraction
            pnl = risk_amount * float(r)
            bank += pnl
            peak = max(peak, bank)
            dd = (bank / peak) - 1
            max_dd = min(max_dd, dd)

        summaries.append({
            'setup_code': str(setup_code),
            'trades': int(len(grp)),
            'win_rate': round(float((grp['r_multiple'] > 0).mean()) * 100, 2),
            'avg_r_multiple': round(float(grp['r_multiple'].mean()), 4),
            'avg_days_held': round(float(grp['days_held'].mean()), 2),
            'avg_concurrent_exposure': round(float(grp['concurrent_positions_at_entry'].mean()), 2),
            'avg_setup_exposure': round(float(grp['setup_positions_at_entry'].mean()), 2),
            'max_concurrent_exposure': int(grp['concurrent_positions_at_entry'].max()),
            'expiry_rate_pct': round(float((grp['exit_reason'] == 'expiry').mean()) * 100, 2),
            'total_return_pct': round(((bank / initial_bank) - 1) * 100, 4),
            'final_bank': round(bank, 2),
            'max_drawdown_pct': round(max_dd * 100, 4),
        })

    summary = pd.DataFrame(summaries).sort_values('final_bank', ascending=False).reset_index(drop=True)
    return trades, summary
