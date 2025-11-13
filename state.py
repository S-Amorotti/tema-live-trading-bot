import json
from typing import Optional, Dict
from config import LAST_BAR_FILE, DAY_START_EQUITY_FILE


def get_last_bar_ts() -> Optional[str]:
    if LAST_BAR_FILE.exists():
        return LAST_BAR_FILE.read_text().strip()
    return None


def set_last_bar_ts(ts_iso: str) -> None:
    LAST_BAR_FILE.write_text(ts_iso)


def get_day_start_equity() -> Optional[Dict]:
    if DAY_START_EQUITY_FILE.exists():
        try:
            return json.loads(DAY_START_EQUITY_FILE.read_text())
        except Exception:
            return None
    return None


def set_day_start_equity(date_key: str, equity: float):
    payload = {"date": date_key, "equity": float(equity)}
    DAY_START_EQUITY_FILE.write_text(json.dumps(payload))
