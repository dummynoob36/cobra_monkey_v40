# Cobra Monkey v40 — Operating Model (Next)

## Objective
Turn Cobra Monkey from a daily signal detector into a practical daily portfolio operator with:
- controlled entries
- explicit exits
- persistent portfolio state
- Telegram delivery for actionable decisions

## Valid setups only
The live system remains limited to:
- `A_REV_US`
- `A_REV_GLOBAL`
- `D_EU_TACTICAL`

Everything else stays outside the operational flow unless new evidence appears.

## Daily execution model
### 1. Daily data refresh
The system should run once per trading day after the largest share of relevant markets have printed their daily bar.

Recommended production window:
- **22:45 UTC Monday-Friday**

Why:
- US cash market is closed by then
- EU markets are long closed
- daily bars from Yahoo/yfinance are usually available and stabilized
- avoids running too early while US session is still open

### 2. Build daily dataset
- refresh OHLCV universe
- compute indicators
- derive setup, score, quality, exit template
- keep only operationally valid setups

### 3. Portfolio lifecycle
Each run updates a persistent portfolio file:
- `data/portfolio_v40.csv`

Per run:
1. close positions whose stop/target/expiry condition is now known from daily data
2. evaluate today's new candidates
3. select entries under operational constraints
4. persist the updated portfolio
5. notify Telegram

## Operational constraints
### Global baseline
- `max_concurrent_positions = 8`
- `cooldown_days = 10`

### Setup caps
- `A_REV_US = 2`
- `A_REV_GLOBAL = 4`
- `D_EU_TACTICAL = 2`

### Entry priority
When capacity is constrained:
1. higher `signal_score`
2. quality tier
3. deterministic ticker ordering

## Exit model
The live system is daily-bar based, not intraday execution.

### Exit reasons
- `target`
- `stop`
- `expiry`

### Current templates
- `A_REV_US`: 1.3 ATR stop / 1.9 ATR target / 7d horizon
- `A_REV_GLOBAL`: 1.2 ATR stop / 1.8 ATR target / 7d horizon
- `D_EU_TACTICAL`: 1.0 ATR stop / 1.4 ATR target / 5d horizon

## Telegram delivery model
Telegram should receive **operational messages**, not just raw pattern summaries.

### Message types
1. **Daily operational summary**
   - valid signals found
   - active baseline
   - setup caps

2. **Entry alert**
   - only for selected entries actually admitted into portfolio
   - fields:
     - ticker
     - setup
     - score
     - entry
     - stop
     - target
     - horizon

3. **Exit alert**
   - only for positions closed that day
   - fields:
     - ticker
     - setup
     - exit reason
     - exit price
     - pnl %

4. **Portfolio status**
   - currently open positions
   - entry / stop / target

5. **Optional research summary**
   - useful during testing
   - should be removable or downgraded later to reduce noise

## Definitive system behavior
### During test phase
Send:
- summary
- entries
- exits
- portfolio status
- optional simple summary

### During production phase
Prefer sending only:
- entries
- exits
- compact portfolio state when changed

The more analytical messages should become optional.

## Data timing notes
### What matters most
For a daily system, the key is not "maximum markets open".
The key is:
- bars are closed
- data provider has published stable daily candles
- the run happens consistently at the same time

### Recommendation
Avoid running during overlapping live market hours for the main official run.
A daily system should run **after close**, not while markets are still forming bars.

### Optional future split
If needed later:
- **refresh run** around 17:30 UTC to collect intermediate context
- **official operational run** around 22:45 UTC for final decisions

For now: one official run is enough.

## Before GitHub testing
Need to ensure:
1. Telegram credentials exist in GitHub Secrets
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. workflow uploads/stores:
   - `data/portfolio_v40.csv`
   - `data/dataset_v40.csv`
3. portfolio persistence is compatible with GitHub execution model
4. production workflow commits required state changes safely

## Important caveat
If GitHub Actions is the execution host, `portfolio_v40.csv` must persist across runs.
That means one of:
- commit portfolio file back to repo
- store/load state from artifact or external store
- move operational runtime to a persistent host

For real daily operations, a persistent host is preferable to ephemeral CI.

## Recommended rollout
### Phase 1
- finish live portfolio flow locally
- verify Telegram formatting
- verify entry/exit correctness

### Phase 2
- choose persistent runtime host
- schedule daily run at 22:45 UTC
- test for 1-2 weeks in paper mode

### Phase 3
- push to GitHub / production runtime
- reduce noise in Telegram
- optionally add FinceptTerminal as operator dashboard

## FinceptTerminal role
FinceptTerminal should be used as:
- visualization / monitoring layer
- signal ranking panel
- portfolio exposure dashboard
- drill-down tool

It should not replace Cobra's core signal, exit, or portfolio logic.
