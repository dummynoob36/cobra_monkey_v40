import pandas as pd

from v40.setup_definitions import derive_setup, derive_trade_plan


def test_derive_setup_for_a_us():
    setup, note, horizon = derive_setup(pd.Series({
        'pattern_family': 'A',
        'trend_regime': 'DOWN',
        'market_bucket': 'US_OR_OTHER',
    }))
    assert setup == 'A_REV_US'
    assert horizon == 10


def test_derive_trade_plan_returns_prices_when_atr_present():
    style, entry, stop, target = derive_trade_plan(pd.Series({
        'pattern_family': 'E',
        'trend_regime': 'UP',
        'market_bucket': 'EU',
        'close': 100.0,
        'atr14': 5.0,
    }))
    assert style == 'compression_breakout_followthrough'
    assert entry == 100.0
    assert stop < entry
    assert target > entry
