from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DASH = ROOT / 'dashboards'
OUT_JSON = DASH / 'fincept_terminal_dashboard.json'
OUT_MD = DASH / 'fincept_terminal_dashboard.md'
OUT_HTML = DASH / 'fincept_terminal_dashboard.html'
PORTFOLIO = DATA / 'portfolio_v40.csv'
DATASET = DATA / 'dataset_v40.csv'
PRICES_DIR = ROOT / 'outputs' / 'daily_prices'
SETUP_CAPS = {'A_REV_US': 2, 'A_REV_GLOBAL': 4, 'D_EU_TACTICAL': 2}
MAX_CONCURRENT = 8


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _to_date(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors='coerce')
    return out


def _json_default(obj):
    if pd.isna(obj):
        return None
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return str(obj)


def _round_or_none(value, digits: int = 2):
    if value is None or pd.isna(value):
        return None
    try:
        return round(float(value), digits)
    except Exception:
        return None


def _load_latest_close(ticker: str):
    path = PRICES_DIR / f'{ticker}.csv'
    if not path.exists():
        return None, None
    try:
        df = pd.read_csv(path)
        if df.empty or 'close' not in df.columns or 'date' not in df.columns:
            return None, None
        row = df.iloc[-1]
        return _round_or_none(row.get('close')), str(pd.to_datetime(row.get('date'), errors='coerce').date()) if pd.notna(pd.to_datetime(row.get('date'), errors='coerce')) else None
    except Exception:
        return None, None


def build_payload() -> dict:
    portfolio = _to_date(_load_csv(PORTFOLIO), ['signal_date', 'opened_at', 'planned_exit_date', 'closed_at'])
    dataset = _to_date(_load_csv(DATASET), ['signal_date'])

    open_positions = portfolio[portfolio.get('status', pd.Series(dtype=str)) == 'open'].copy() if not portfolio.empty else pd.DataFrame()
    closed_positions = portfolio[portfolio.get('status', pd.Series(dtype=str)) == 'closed'].copy() if not portfolio.empty else pd.DataFrame()

    if not dataset.empty and 'signal_status' in dataset.columns:
        dataset = dataset[dataset['signal_status'] != 'disabled'].copy()

    latest_signal_date = None
    today_candidates = pd.DataFrame()
    if not dataset.empty and 'signal_date' in dataset.columns:
        latest_signal_date = dataset['signal_date'].max()
        today_candidates = dataset[dataset['signal_date'] == latest_signal_date].copy()
        sort_cols = [c for c in ['signal_score', 'quality_tier', 'ticker'] if c in today_candidates.columns]
        asc = [False if c == 'signal_score' else True for c in sort_cols]
        if sort_cols:
            today_candidates = today_candidates.sort_values(sort_cols, ascending=asc)

    total_realized = float(closed_positions['pnl_pct'].fillna(0).sum()) if not closed_positions.empty and 'pnl_pct' in closed_positions.columns else 0.0
    avg_realized = float(closed_positions['pnl_pct'].dropna().mean()) if not closed_positions.empty and 'pnl_pct' in closed_positions.columns and not closed_positions['pnl_pct'].dropna().empty else None
    win_rate = float((closed_positions['pnl_pct'] > 0).mean() * 100) if not closed_positions.empty and 'pnl_pct' in closed_positions.columns and not closed_positions['pnl_pct'].dropna().empty else None

    setup_usage = []
    open_by_setup = open_positions['setup_code'].value_counts().to_dict() if not open_positions.empty and 'setup_code' in open_positions.columns else {}
    for setup, cap in SETUP_CAPS.items():
        used = int(open_by_setup.get(setup, 0))
        setup_usage.append({
            'setup_code': setup,
            'open_positions': used,
            'cap': cap,
            'remaining': max(cap - used, 0),
            'usage_pct': _round_or_none((used / cap) * 100 if cap else None),
        })

    candidate_rows = []
    for _, row in today_candidates.head(12).iterrows():
        candidate_rows.append({
            'ticker': row.get('ticker'),
            'setup_code': row.get('setup_code'),
            'quality_tier': row.get('quality_tier'),
            'signal_score': _round_or_none(row.get('signal_score'), 0),
            'entry_price': _round_or_none(row.get('entry_price')),
            'stop_price': _round_or_none(row.get('stop_price')),
            'target_price': _round_or_none(row.get('target_price')),
            'market_bucket': row.get('market_bucket'),
        })

    open_rows = []
    live_unrealized_sum = 0.0
    unrealized_count = 0
    if not open_positions.empty:
        for _, row in open_positions.sort_values(['setup_code', 'signal_score', 'ticker'], ascending=[True, False, True]).iterrows():
            ticker = row.get('ticker')
            last_close, last_close_date = _load_latest_close(str(ticker))
            entry_price = _round_or_none(row.get('entry_price'))
            unrealized_pct = None
            if last_close is not None and entry_price not in (None, 0):
                unrealized_pct = _round_or_none(((last_close / entry_price) - 1) * 100)
                if unrealized_pct is not None:
                    live_unrealized_sum += unrealized_pct
                    unrealized_count += 1
            open_rows.append({
                'ticker': ticker,
                'setup_code': row.get('setup_code'),
                'opened_at': None if pd.isna(row.get('opened_at')) else str(pd.to_datetime(row.get('opened_at')).date()),
                'planned_exit_date': None if pd.isna(row.get('planned_exit_date')) else str(pd.to_datetime(row.get('planned_exit_date')).date()),
                'entry_price': entry_price,
                'last_close': last_close,
                'last_close_date': last_close_date,
                'unrealized_pnl_pct': unrealized_pct,
                'stop_price': _round_or_none(row.get('stop_price')),
                'target_price': _round_or_none(row.get('target_price')),
                'signal_score': _round_or_none(row.get('signal_score'), 0),
                'quality_tier': row.get('quality_tier'),
            })

    closed_rows = []
    equity_curve = []
    pnl_by_setup = []
    exit_distribution = []
    if not closed_positions.empty:
        if 'closed_at' in closed_positions.columns:
            closed_positions = closed_positions.sort_values(['closed_at', 'ticker'], ascending=[True, True])
        running = 0.0
        for _, row in closed_positions.iterrows():
            pnl = 0.0 if pd.isna(row.get('pnl_pct')) else float(row.get('pnl_pct'))
            running += pnl
            closed_rows.append({
                'ticker': row.get('ticker'),
                'setup_code': row.get('setup_code'),
                'closed_at': None if pd.isna(row.get('closed_at')) else str(pd.to_datetime(row.get('closed_at')).date()),
                'exit_reason': row.get('exit_reason'),
                'pnl_pct': _round_or_none(row.get('pnl_pct')),
            })
            equity_curve.append({
                'date': None if pd.isna(row.get('closed_at')) else str(pd.to_datetime(row.get('closed_at')).date()),
                'cum_pnl_pct': _round_or_none(running),
            })

        if 'setup_code' in closed_positions.columns and 'pnl_pct' in closed_positions.columns:
            tmp = closed_positions.groupby('setup_code', dropna=False)['pnl_pct'].agg(['count', 'sum', 'mean']).reset_index()
            for _, row in tmp.iterrows():
                pnl_by_setup.append({
                    'setup_code': row['setup_code'],
                    'trades': int(row['count']),
                    'pnl_sum_pct': _round_or_none(row['sum']),
                    'avg_pnl_pct': _round_or_none(row['mean']),
                })

        if 'exit_reason' in closed_positions.columns:
            tmp = closed_positions['exit_reason'].fillna('unknown').value_counts().reset_index()
            tmp.columns = ['exit_reason', 'count']
            exit_distribution = tmp.to_dict(orient='records')

    timeline = []
    if not portfolio.empty and 'opened_at' in portfolio.columns:
        date_points = sorted(set(
            [d for d in pd.to_datetime(portfolio['opened_at'], errors='coerce').dropna().dt.date.tolist()] +
            [d for d in pd.to_datetime(portfolio.get('closed_at'), errors='coerce').dropna().dt.date.tolist()]
        ))
        for dt in date_points:
            open_count = 0
            for _, row in portfolio.iterrows():
                opened = pd.to_datetime(row.get('opened_at'), errors='coerce')
                closed = pd.to_datetime(row.get('closed_at'), errors='coerce')
                if pd.isna(opened):
                    continue
                if opened.date() <= dt and (pd.isna(closed) or closed.date() > dt):
                    open_count += 1
            timeline.append({'date': str(dt), 'open_positions': open_count})

    payload = {
        'snapshot': {
            'latest_signal_date': None if pd.isna(latest_signal_date) else str(pd.to_datetime(latest_signal_date).date()),
            'open_positions': int(len(open_positions)),
            'closed_positions': int(len(closed_positions)),
            'candidate_count_today': int(len(today_candidates)),
            'portfolio_capacity_used': int(len(open_positions)),
            'portfolio_capacity_max': MAX_CONCURRENT,
            'portfolio_capacity_pct': _round_or_none((len(open_positions) / MAX_CONCURRENT) * 100 if MAX_CONCURRENT else None),
            'realized_pnl_pct_sum': _round_or_none(total_realized),
            'avg_closed_trade_pnl_pct': _round_or_none(avg_realized),
            'closed_trade_win_rate_pct': _round_or_none(win_rate),
            'live_unrealized_pnl_pct_sum': _round_or_none(live_unrealized_sum) if unrealized_count else None,
        },
        'setup_usage': setup_usage,
        'open_positions': open_rows,
        'recent_closed_positions': list(reversed(closed_rows[-12:])),
        'top_candidates': candidate_rows,
        'charts': {
            'equity_curve': equity_curve,
            'open_positions_timeline': timeline,
            'pnl_by_setup': pnl_by_setup,
            'exit_distribution': exit_distribution,
        },
    }
    return payload


def build_markdown(payload: dict) -> str:
    s = payload['snapshot']
    lines = ['# FinceptTerminal — Cobra v40 Dashboard', '', '## Snapshot']
    lines.append(f"- Signal date: {s['latest_signal_date']}")
    lines.append(f"- Open positions: {s['open_positions']} / {s['portfolio_capacity_max']} ({s['portfolio_capacity_pct']}%)")
    lines.append(f"- Closed positions: {s['closed_positions']}")
    lines.append(f"- Candidates today: {s['candidate_count_today']}")
    lines.append(f"- Realized PnL sum (%): {s['realized_pnl_pct_sum']}")
    lines.append(f"- Live unrealized PnL sum (%): {s['live_unrealized_pnl_pct_sum']}")
    lines.append(f"- Avg closed trade PnL (%): {s['avg_closed_trade_pnl_pct']}")
    lines.append(f"- Closed trade win rate (%): {s['closed_trade_win_rate_pct']}")
    lines.append('')
    lines.append('## Setup capacity')
    for row in payload['setup_usage']:
        lines.append(f"- {row['setup_code']}: {row['open_positions']} / {row['cap']} used ({row['usage_pct']}%), remaining {row['remaining']}")
    lines.append('')
    lines.append('## Open positions')
    if payload['open_positions']:
        for row in payload['open_positions']:
            lines.append(
                f"- {row['ticker']} · {row['setup_code']} · entry {row['entry_price']} · last {row['last_close']} ({row['last_close_date']}) · uPnL {row['unrealized_pnl_pct']}% · stop {row['stop_price']} · target {row['target_price']} · planned exit {row['planned_exit_date']}"
            )
    else:
        lines.append('- None')
    lines.append('')
    lines.append('## Top candidates')
    if payload['top_candidates']:
        for row in payload['top_candidates']:
            lines.append(f"- {row['ticker']} · {row['setup_code']} · score {row['signal_score']} · quality {row['quality_tier']} · market {row['market_bucket']}")
    else:
        lines.append('- None')
    lines.append('')
    lines.append('## Recent closed positions')
    if payload['recent_closed_positions']:
        for row in payload['recent_closed_positions']:
            lines.append(f"- {row['closed_at']} · {row['ticker']} · {row['setup_code']} · {row['exit_reason']} · {row['pnl_pct']}%")
    else:
        lines.append('- None')
    lines.append('')
    return '\n'.join(lines)


def build_html(payload: dict) -> str:
    data_json = json.dumps(payload, default=_json_default)
    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>FinceptTerminal — Cobra v40 Dashboard</title>
  <script src=\"https://cdn.plot.ly/plotly-2.35.2.min.js\"></script>
  <style>
    :root {{
      --bg:#08111f; --bg2:#0f1b31; --card:#101c32cc; --line:#233556; --text:#e8eefc; --muted:#94a7cc;
      --green:#34d399; --blue:#60a5fa; --amber:#f59e0b; --pink:#f472b6;
    }}
    * {{ box-sizing:border-box; }}
    body {{ font-family: Inter, ui-sans-serif, system-ui, Arial, sans-serif; margin:0; background:radial-gradient(circle at top, #132445 0%, var(--bg) 55%); color:var(--text); }}
    .wrap {{ max-width: 1400px; margin:0 auto; padding:32px 20px 48px; }}
    .hero {{ display:flex; justify-content:space-between; align-items:end; gap:24px; margin-bottom:22px; }}
    h1 {{ margin:0; font-size:34px; }}
    .muted {{ color:var(--muted); font-size:14px; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin:18px 0 26px; }}
    .card {{ background:var(--card); backdrop-filter: blur(10px); border:1px solid var(--line); border-radius:18px; padding:18px; box-shadow:0 10px 35px rgba(0,0,0,.22); }}
    .metric {{ font-size:30px; font-weight:700; margin-top:6px; }}
    .section {{ margin-top:24px; }}
    .section-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
    .charts {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th,td {{ border-bottom:1px solid var(--line); padding:10px 8px; text-align:left; }}
    th {{ color:#b7c5e4; font-weight:600; }}
    .pill {{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; border:1px solid var(--line); color:#d9e4ff; background:#132441; }}
    .good {{ color:var(--green); }} .bad {{ color:#fb7185; }} .accent {{ color:#8b5cf6; }}
    @media (max-width: 980px) {{ .charts {{ grid-template-columns:1fr; }} .hero {{ flex-direction:column; align-items:flex-start; }} }}
  </style>
</head>
<body>
<div class=\"wrap\">
  <div class=\"hero\">
    <div>
      <div class=\"pill\">FinceptTerminal / Cobra v40</div>
      <h1>Portfolio Monitor</h1>
      <div class=\"muted\">Live paper-trading oversight with cleaner operational metrics</div>
    </div>
    <div class=\"muted\">Signal date: <strong>{payload['snapshot']['latest_signal_date'] or '-'}</strong></div>
  </div>

  <div id=\"snapshot\" class=\"grid\"></div>

  <div class=\"section\">
    <div class=\"section-head\"><h2>Charts</h2><div class=\"muted\">Clean dates, no timestamp noise</div></div>
    <div class=\"charts\">
      <div class=\"card\"><div id=\"equityCurve\"></div></div>
      <div class=\"card\"><div id=\"exposureTimeline\"></div></div>
      <div class=\"card\"><div id=\"setupPnl\"></div></div>
      <div class=\"card\"><div id=\"exitDistribution\"></div></div>
    </div>
  </div>

  <div class=\"section card\"><div class=\"section-head\"><h2>Setup capacity</h2></div><table id=\"setupTable\"></table></div>
  <div class=\"section card\"><div class=\"section-head\"><h2>Open positions</h2><div class=\"muted\">Includes latest close and unrealized PnL</div></div><table id=\"openTable\"></table></div>
  <div class=\"section card\"><div class=\"section-head\"><h2>Top candidates</h2></div><table id=\"candidateTable\"></table></div>
  <div class=\"section card\"><div class=\"section-head\"><h2>Recent closed positions</h2></div><table id=\"closedTable\"></table></div>
</div>

<script>
const payload = {data_json};
function fmt(v, suffix='') {{ return (v === null || v === undefined || v === '') ? '-' : `${{v}}${{suffix}}`; }}
function card(title, value, extra='') {{ return `<div class="card"><div class="muted">${{title}}</div><div class="metric">${{value}}</div><div class="muted">${{extra}}</div></div>`; }}
const s = payload.snapshot;
document.getElementById('snapshot').innerHTML = [
  card('Open positions', `${{s.open_positions}} / ${{s.portfolio_capacity_max}}`, `capacity used ${{fmt(s.portfolio_capacity_pct, '%')}}`),
  card('Candidates today', s.candidate_count_today),
  card('Realized PnL', fmt(s.realized_pnl_pct_sum, '%')),
  card('Live unrealized PnL', fmt(s.live_unrealized_pnl_pct_sum, '%')),
  card('Closed positions', s.closed_positions),
  card('Closed win rate', fmt(s.closed_trade_win_rate_pct, '%')),
].join('');

function renderTable(id, rows) {{
  const el = document.getElementById(id);
  if (!rows || !rows.length) {{ el.innerHTML = '<tr><td>No data</td></tr>'; return; }}
  const cols = Object.keys(rows[0]);
  const thead = '<tr>' + cols.map(c => `<th>${{c}}</th>`).join('') + '</tr>';
  const tbody = rows.map(r => '<tr>' + cols.map(c => `<td>${{r[c] ?? ''}}</td>`).join('') + '</tr>').join('');
  el.innerHTML = thead + tbody;
}}
renderTable('setupTable', payload.setup_usage);
renderTable('openTable', payload.open_positions);
renderTable('candidateTable', payload.top_candidates);
renderTable('closedTable', payload.recent_closed_positions);

const baseLayout = {{ paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{{color:'#e8eefc'}}, margin:{{t:42,r:18,b:42,l:42}} }};
const eq = payload.charts.equity_curve || [];
Plotly.newPlot('equityCurve', [{{ x:eq.map(r=>r.date), y:eq.map(r=>r.cum_pnl_pct), type:'scatter', mode:'lines+markers', line:{{color:'#34d399', width:3}}, marker:{{size:8}} }}], {{ ...baseLayout, title:'Equity curve (realized PnL %)' }}, {{displayModeBar:false}});
const ex = payload.charts.open_positions_timeline || [];
Plotly.newPlot('exposureTimeline', [{{ x:ex.map(r=>r.date), y:ex.map(r=>r.open_positions), type:'bar', marker:{{color:'#60a5fa', opacity:.9}} }}], {{ ...baseLayout, title:'Open positions over time' }}, {{displayModeBar:false}});
const sp = payload.charts.pnl_by_setup || [];
Plotly.newPlot('setupPnl', [{{ x:sp.map(r=>r.setup_code), y:sp.map(r=>r.pnl_sum_pct), type:'bar', marker:{{color:'#f59e0b'}} }}], {{ ...baseLayout, title:'Realized PnL by setup (%)' }}, {{displayModeBar:false}});
const ed = payload.charts.exit_distribution || [];
Plotly.newPlot('exitDistribution', [{{ labels:ed.map(r=>r.exit_reason), values:ed.map(r=>r.count), type:'pie', hole:.55, textinfo:'label+percent', marker:{{colors:['#34d399','#fb7185','#60a5fa','#f59e0b']}} }}], {{ ...baseLayout, title:'Exit distribution' }}, {{displayModeBar:false}});
</script>
</body>
</html>"""


def main() -> None:
    payload = build_payload()
    OUT_JSON.write_text(json.dumps(payload, indent=2, default=_json_default), encoding='utf-8')
    OUT_MD.write_text(build_markdown(payload), encoding='utf-8')
    OUT_HTML.write_text(build_html(payload), encoding='utf-8')
    print(f'Wrote {OUT_JSON}')
    print(f'Wrote {OUT_MD}')
    print(f'Wrote {OUT_HTML}')


if __name__ == '__main__':
    main()
