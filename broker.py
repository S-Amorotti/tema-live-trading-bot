import math
import numpy as np
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import (
    MarketOrderRequest,
    TakeProfitRequest,
    StopLossRequest
)
from config import (
    API_KEY,
    API_SECRET,
    PAPER,
    IS_CRYPTO,
    MIN_ATR,
    VOL_TARGET,
    MAX_QTY,
    ATR_TRAIL_MULT
)


def make_trading_client() -> TradingClient:
    assert API_KEY and API_SECRET, "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your environment."
    return TradingClient(API_KEY, API_SECRET, paper=PAPER)


def get_equity(trading: TradingClient) -> float:
    acct = trading.get_account()
    try:
        return float(acct.equity)
    except Exception:
        return float(acct.cash)


def get_position_side_qty(trading: TradingClient, symbol: str):
    """
    Return (side, qty): side ∈ {-1,0,1}, qty absolute.
    """
    try:
        pos = trading.get_open_position(symbol)
        qty = float(pos.qty)
        side = 1 if qty > 0 else -1
        return side, abs(qty)
    except Exception:
        return 0, 0.0


def flatten_if_opposite(
        trading: TradingClient, symbol: str,
        desired_side: int
        ):
    current_side, _ = get_position_side_qty(trading, symbol)
    if current_side != 0 and current_side != desired_side:
        trading.close_position(symbol)


def atr_position_size(equity: float, atr: float, price: float) -> float:
    """
    ATR-based position sizing, clipped so notional <= equity
    and capped by MAX_QTY. Works for both equities and crypto.
    """
    if np.isnan(atr) or atr < MIN_ATR or price <= 0:
        return 0.0

    # Risk capital based on VOL_TARGET
    dollar_risk = equity * VOL_TARGET

    # ATR-based raw size (your original formula with scaling)
    raw_qty = (dollar_risk / (atr * 4)) * 3

    # Clip by maximum quantity
    raw_qty = min(raw_qty, MAX_QTY)

    # Ensure notional <= equity
    max_by_equity = equity / price
    qty = min(raw_qty, max_by_equity, MAX_QTY)

    # Floor for equities, float for crypto
    if IS_CRYPTO:
        return float(max(0.0, qty))
    return float(max(0, math.floor(qty)))


def submit_bracket_market(trading: TradingClient,
                          symbol: str, side: int, qty: float,
                          last_close: float, atr: float):
    """
    Market entry with TP/SL approximating your backtest
    (TP=±3*ATR, SL=∓ATR_TRAIL_MULT*ATR).
    """
    if qty <= 0 or side not in (-1, 1):
        return None

    if side == 1:
        tp_price = round(last_close + 3 * atr, 2)
        sl_price = round(last_close - ATR_TRAIL_MULT * atr, 2)
        order_side = OrderSide.BUY
    else:
        tp_price = round(last_close - 3 * atr, 2)
        sl_price = round(last_close + ATR_TRAIL_MULT * atr, 2)
        order_side = OrderSide.SELL

    try:
        return trading.submit_order(order_data=MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=tp_price),
            stop_loss=StopLossRequest(stop_price=sl_price)
        ))
    except Exception as e:
        print(f"[WARN] Bracket rejected({e}). Submitting simple market order.")
        return trading.submit_order(order_data=MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.GTC
        ))


def is_market_open(trading: TradingClient) -> bool:
    """
    For equities only. Crypto trades 24/7, so return True in that case.
    """
    if IS_CRYPTO:
        return True
    try:
        clock = trading.get_clock()
        return bool(clock.is_open)
    except Exception:
        return True  # fail-open
