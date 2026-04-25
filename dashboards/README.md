# Dashboards

## FinceptTerminal dashboard for Cobra v40

Generated artifacts:
- `dashboards/fincept_terminal_dashboard.json`
- `dashboards/fincept_terminal_dashboard.md`
- `dashboards/fincept_terminal_dashboard.html`

Build/update it with:

```bash
cd ~/.openclaw/workspace/cobra_monkey_v40
. .venv/bin/activate
python dashboards/build_fincept_terminal_dashboard.py
```

What it includes:
- portfolio snapshot
- setup capacity usage
- open positions
- recent closed positions
- top current candidates
- equity curve chart
- open exposure timeline
- realized pnl by setup
- exit distribution

Suggested FinceptTerminal panels:
1. Portfolio snapshot KPIs
2. Setup capacity / exposure
3. Open positions table
4. Top candidates table
5. Closed trades / realized pnl log
6. Equity curve
7. Exposure timeline
8. PnL by setup / exit distribution

To view it locally in a browser:

```bash
cd ~/.openclaw/workspace/cobra_monkey_v40
python3 -m http.server 8000
```

Then open:
- `http://localhost:8000/dashboards/fincept_terminal_dashboard.html`
