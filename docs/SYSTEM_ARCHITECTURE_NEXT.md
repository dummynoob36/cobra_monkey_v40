# Cobra Monkey → Systematic Signal Engine (Next Architecture)

## Goal
Move from a pattern-alert script to a systematic signal engine with four clear layers:

1. **Data Layer**
   - universe management
   - daily prices
   - optional macro / sentiment / alternative data

2. **Research Layer**
   - feature engineering
   - pattern definitions
   - forward-return validation
   - regime/market segmentation

3. **Signal Layer**
   - pattern detection
   - quality tier
   - signal score
   - report generation

4. **Operator Layer**
   - Telegram / alerts
   - dashboard / terminal UI
   - paper trading / execution adapters later

## What Cobra Monkey should own
- dataset generation
- pattern definitions
- validation metrics
- quality + score computation
- daily batch reports

## What FinceptTerminal can add
FinceptTerminal should be treated as the **operator + research UI**, not as the pattern engine itself.

Useful integration targets:
- dashboard for ranked signals
- drill-down per ticker
- market context and cross-asset overlays
- portfolio/risk panels
- paper trading / execution tracking UI
- node-editor or workflow layer for orchestration later

## Immediate priorities
1. Keep improving pattern validity before adding complexity.
2. Promote only patterns with stable evidence.
3. Downrank or hide low-quality signals.
4. Expand universe gradually, then rerun validation.
5. Add broker/paper-trade layer only after score stability improves.

## Current empirical direction
- Prioritize pattern A, especially US.
- Use pattern E mainly in UP regimes and short horizons.
- Treat D only as speculative in select EU contexts.
- De-emphasize E-Prime until it actually appears and validates.

## Next implementation ideas
- introduce `signal_status` (new, active, expired, closed)
- add entry/stop/target templates per pattern family
- add regime-specific score multipliers
- compute rolling performance decay by pattern
- add benchmark comparison per market bucket
