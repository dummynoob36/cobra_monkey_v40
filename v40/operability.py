from __future__ import annotations

from dataclasses import dataclass

VALID_SETUPS = ('A_REV_US', 'A_REV_GLOBAL', 'D_EU_TACTICAL')
DEFAULT_BASELINE_MAX_CONCURRENT = 8
DEFAULT_BASELINE_COOLDOWN_DAYS = 10
DEFAULT_SETUP_CAPS: dict[str, int] = {
    'A_REV_US': 2,
    'A_REV_GLOBAL': 4,
    'D_EU_TACTICAL': 2,
}


@dataclass(frozen=True)
class ExitPolicy:
    stop_atr_mult: float
    target_atr_mult: float
    horizon_days: int
    exit_style: str


EXIT_POLICY_BY_SETUP: dict[str, ExitPolicy] = {
    'A_REV_US': ExitPolicy(
        stop_atr_mult=1.3,
        target_atr_mult=1.9,
        horizon_days=7,
        exit_style='mean_reversion_reversal_fast',
    ),
    'A_REV_GLOBAL': ExitPolicy(
        stop_atr_mult=1.2,
        target_atr_mult=1.8,
        horizon_days=7,
        exit_style='mean_reversion_reversal_defensive',
    ),
    'D_EU_TACTICAL': ExitPolicy(
        stop_atr_mult=1.0,
        target_atr_mult=1.4,
        horizon_days=5,
        exit_style='tactical_pullback_compact',
    ),
}


def get_exit_policy(setup_code: str) -> ExitPolicy | None:
    return EXIT_POLICY_BY_SETUP.get(str(setup_code))
