import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env that sits next to this file, regardless of your working dir
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# --- API ---
API_KEY = os.getenv("APCA_API_KEY_ID")
API_SECRET = os.getenv("APCA_API_SECRET_KEY")
PAPER = True  # paper trading

# --- WHAT TO TRADE ---
IS_CRYPTO = True
SYMBOL = "BTC/USD" if IS_CRYPTO else "SPY"

# --- STRATEGY / RISK ---
BASE_EQUITY = 10_000

# Per-trade risk (lowered)
VOL_TARGET = 0.01           # was 0.02 → cut per-trade risk in half

# Execution / stops
ATR_TRAIL_MULT = 2.5
MIN_ATR = 1.0
MAX_QTY = 3.0               # was 5.0 → cap gross size a bit

# Entry filters
ADX_THRESHOLD = 25
CMO_THRESHOLD = 20   # entry filter keeps using CMO; we’ll also size by CMO

# Extra safety knobs (new)
VOL_SPIKE_CAP = 0.012       # skip entries if ATR/price > 1.2%
COOLDOWN_MIN = 60        # pause this many minutes after a stop-out
CMO_SIZE_FLOOR = 0.35  # min sizing multiplier when momentum is weak (0.0..1.0)

# --- DATA ---
LOOKBACK_1H = 300           # enough for TEMA(80)
LOOKBACK_4H = 300           # enough for TEMA(70)
POLL_SECONDS = 60

# --- RISK GUARD (optional) ---
ENABLE_DAILY_LOSS_GUARD = False
MAX_DAILY_DRAWDOWN_PCT = 0.05  # pause for today if equity drop > 5%

# ---- Debug ----
DEBUG_SIGNALS = True

# --- FILES / FOLDERS ---
ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"
LOG_DIR.mkdir(exist_ok=True, parents=True)
STATE_DIR.mkdir(exist_ok=True, parents=True)

LAST_BAR_FILE = STATE_DIR / "last_bar.txt"
DAY_START_EQUITY_FILE = STATE_DIR / "day_start_equity.txt"
ORDER_LOG = LOG_DIR / "orders.csv"
EVENT_LOG = LOG_DIR / "events.log"
