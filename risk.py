from config import ENABLE_DAILY_LOSS_GUARD, MAX_DAILY_DRAWDOWN_PCT
from state import get_day_start_equity, set_day_start_equity


def update_day_start_equity_if_new_day(now_utc, equity: float):
    """
    Persist day-start equity once per UTC day (simple approach).
    """
    key = now_utc.strftime("%Y-%m-%d")
    stored = get_day_start_equity()
    if not stored or stored["date"] != key:
        set_day_start_equity(key, equity)


def should_pause_trading(equity: float) -> bool:
    """
    Pause for the day if equity drawdown vs day start breaches threshold.
    """
    if not ENABLE_DAILY_LOSS_GUARD:
        return False
    stored = get_day_start_equity()
    if not stored:
        return False
    start_eq = stored["equity"]
    if start_eq <= 0:
        return False
    dd = (start_eq - equity) / start_eq
    return dd >= MAX_DAILY_DRAWDOWN_PCT
