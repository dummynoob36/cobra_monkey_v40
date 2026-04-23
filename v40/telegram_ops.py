from __future__ import annotations

from typing import List

import pandas as pd

from v40.operability import DEFAULT_BASELINE_COOLDOWN_DAYS, DEFAULT_BASELINE_MAX_CONCURRENT, DEFAULT_SETUP_CAPS
from scripts.telegram.telegram_formatter import build_message


def _quality_icon(value: str) -> str:
    return {
        'HIGH': '🔥',
        'MEDIUM': '✅',
        'SPECULATIVE': '🧪',
        'LOW': '⚪',
        'AVOID': '⛔',
    }.get(str(value), '')


def build_entry_alert(selected_signals: pd.DataFrame, analysis_date: str) -> str:
    count = len(selected_signals) if selected_signals is not None else 0
    summary_lines = [
        f'Entradas nuevas activadas: {count}',
        f'Capacidad global: {DEFAULT_BASELINE_MAX_CONCURRENT} | cooldown: {DEFAULT_BASELINE_COOLDOWN_DAYS}d',
        f"Cupos: US={DEFAULT_SETUP_CAPS.get('A_REV_US', '-')}, GLOBAL={DEFAULT_SETUP_CAPS.get('A_REV_GLOBAL', '-')}, D_EU={DEFAULT_SETUP_CAPS.get('D_EU_TACTICAL', '-')}",
    ]
    data_lines: List[str] = []

    if selected_signals is None or selected_signals.empty:
        return ''
    else:
        data_lines.append('Nuevas posiciones:')
        for _, row in selected_signals.iterrows():
            q = _quality_icon(str(row.get('quality_tier', '')))
            data_lines.append(
                f"• ENTRY {row['ticker']} · {row['setup_code']} {q} · score {int(row.get('signal_score', 0) or 0)}"
                f" · entry {float(row['entry_price']):.2f} · stop {float(row['stop_price']):.2f}"
                f" · target {float(row['target_price']):.2f} · horizon {int(row.get('holding_horizon_days', 0) or 0)}d"
            )

    return build_message(
        phase='🐍 Cobra v4.0 · Entradas',
        date=analysis_date,
        status='OK',
        summary_lines=summary_lines,
        data_lines=data_lines,
    )


def build_exit_alert(closed_positions: pd.DataFrame, analysis_date: str) -> str:
    count = len(closed_positions) if closed_positions is not None else 0
    summary_lines = [f'Salidas detectadas: {count}']
    data_lines: List[str] = []

    if closed_positions is None or closed_positions.empty:
        return ''
    else:
        data_lines.append('Posiciones cerradas:')
        for _, row in closed_positions.iterrows():
            pnl = row.get('pnl_pct')
            pnl_txt = f"{float(pnl):+.2f}%" if pd.notna(pnl) else 'N/A'
            data_lines.append(
                f"• EXIT {row['ticker']} · {row['setup_code']} · {row.get('exit_reason', 'exit')}"
                f" · exit {float(row['exit_price']):.2f} · pnl {pnl_txt}"
            )

    return build_message(
        phase='🐍 Cobra v4.0 · Salidas',
        date=analysis_date,
        status='OK',
        summary_lines=summary_lines,
        data_lines=data_lines,
    )


def build_portfolio_status_alert(portfolio: pd.DataFrame, analysis_date: str) -> str:
    if portfolio is None or portfolio.empty:
        open_positions = pd.DataFrame()
    else:
        open_positions = portfolio[portfolio['status'] == 'open'].copy()

    summary_lines = [
        f'Posiciones abiertas: {len(open_positions)}',
    ]
    data_lines: List[str] = []

    if open_positions.empty:
        return ''
    else:
        data_lines.append('Cartera viva:')
        for _, row in open_positions.sort_values(['setup_code', 'signal_score', 'ticker'], ascending=[True, False, True]).iterrows():
            data_lines.append(
                f"• {row['ticker']} · {row['setup_code']} · entry {float(row['entry_price']):.2f}"
                f" · stop {float(row['stop_price']):.2f} · target {float(row['target_price']):.2f}"
            )

    return build_message(
        phase='🐍 Cobra v4.0 · Estado cartera',
        date=analysis_date,
        status='OK',
        summary_lines=summary_lines,
        data_lines=data_lines,
    )
