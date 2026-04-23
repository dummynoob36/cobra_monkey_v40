# Setup Refinement Notes

## Objective
Reduce drawdown and overtrading while keeping only the three validated setups:
- A_REV_US
- A_REV_GLOBAL
- D_EU_TACTICAL

## Signal load observations
Combined load across the three setups:
- avg signals/day: 7.33
- median signals/day: 4
- p90 signals/day: 15.1
- max signals/day: 155

This is too noisy for systematic execution without filtering.

## Useful refinements found
### A_REV_US
Base:
- 1325 signals
- avg/day 4.09
- hit5 58.04%
- avg5 1.2573%

Refined with RSI < 28:
- 723 signals
- avg/day 2.98
- hit5 60.03%
- avg5 1.4535%
- avg20 3.0513%

Interpretation: better precision and lower operational load.

### A_REV_GLOBAL
Base:
- 1525 signals
- avg/day 4.71
- hit5 58.43%
- avg20 3.4152%

Refined with RSI < 30:
- 999 signals
- avg/day 3.84
- hit5 58.96%
- avg10 1.9202%
- avg20 3.8773%

Interpretation: modest but real improvement.

### D_EU_TACTICAL
Base:
- 448 signals
- avg/day 2.15
- hit5 61.61%
- avg5 1.1185%

Tested filters did not improve it materially.
Current recommendation: keep base version for now.

## Next refinements to test
- cap simultaneous positions
- add minimum spacing/cooldown by ticker
- add market regime confirmation from index breadth or benchmark trend
- test tighter exits for D_EU_TACTICAL
- test partial profit-taking for A_REV_GLOBAL
