'''⚠️ Disclaimer

This software is provided for educational and research purposes only.
It does not constitute financial, trading, or investment advice.
The authors assume no responsibility for any losses, damages, or issues arising
from the use of this code.

Use entirely at your own risk.
'''

import time
import traceback
from datetime import datetime, timezone

from config import (
    SYMBOL, IS_CRYPTO, POLL_SECONDS,
    ADX_THRESHOLD, VOL_SPIKE_CAP, CMO_SIZE_FLOOR,
    CMO_THRESHOLD, MAX_QTY, DEBUG_SIGNALS, BASE_EQUITY
)

from data import get_1h_and_4h
from strategy import compute_signals
from broker import (
    make_trading_client, get_equity, atr_position_size,
    flatten_if_opposite, submit_bracket_market, is_market_open
)
from logger import log_event, log_order
from state import get_last_bar_ts, set_last_bar_ts
from risk import update_day_start_equity_if_new_day, should_pause_trading


def main():
    trading = make_trading_client()
    last_processed_iso = get_last_bar_ts()

    print(f" TEMA live trading - PAPER ==\nSymbol:{SYMBOL}|Crypto:{IS_CRYPTO}")
    log_event("starting bot")

    while True:
        try:
            # Market-hours gate (equities only;
            # for crypto this should return True)
            # Crypto runs 24/7; only gate equities
            if (not IS_CRYPTO) and (not is_market_open(trading)):
                log_event("market closed; sleeping")
                print("market closed; sleeping")  # visible heartbeat
                time.sleep(POLL_SECONDS)
                continue

            # ---- Data ----
            df_1h, df_4h = get_1h_and_4h(SYMBOL)
            if df_1h.empty or df_4h.empty:
                time.sleep(POLL_SECONDS)
                continue

            sig = compute_signals(df_1h, df_4h)
            if sig.empty:
                time.sleep(POLL_SECONDS)
                continue

            # TEMP: sanity check last 3 rows
            cols = ["TEMA10", "TEMA80", "4h_TEMA20", "4h_TEMA70",
                    "ADX", "CMO", "ATR",
                    "ShortTrend_prev", "LongTrend_prev", "ADX_prev",
                    "ADX_slope_prev", "CMO_prev",
                    "long_signal", "short_signal", "entry_dir"]

            # Work strictly on the last CLOSED 1h bar
            last_ts = sig.index[-1]  # tz-aware
            last_iso = last_ts.isoformat()

            # Skip if we've already handled this bar
            if last_processed_iso is not None and last_iso <= last_processed_iso:
                time.sleep(POLL_SECONDS)
                continue

            # Persist immediately so a crash won't cause double-trade
            last_processed_iso = last_iso
            set_last_bar_ts(last_processed_iso)

            row = sig.iloc[-1]
            atr = float(row.get("ATR", 0.0))
            entry_dir = int(row.get("entry_dir", 0))
            close = float(row["close"])

            # ---- Debug: why no entry? ----
            if entry_dir == 0:
                if DEBUG_SIGNALS:
                    def _to_float(x):
                        try:
                            return float(x)
                        except Exception:
                            return None

                    vals = {
                        "ShortTrend_prev": row.get("ShortTrend_prev"),
                        "LongTrend_prev":  row.get("LongTrend_prev"),
                        "ADX_prev":        row.get("ADX_prev"),
                        "ADX_slope_prev":  row.get("ADX_slope_prev"),
                        "CMO_prev":        row.get("CMO_prev"),
                    }
                    vals_str = {k: _to_float(v) for k, v in vals.items()}

                    gates = {
                        "1h&4h LONG trends": (row.get("ShortTrend_prev", 0) == 1) and (row.get("LongTrend_prev", 0) == 1),
                        "1h&4h SHORT trends": (row.get("ShortTrend_prev", 1) == 0) and (row.get("LongTrend_prev", 1) == 0),
                        "ADX_prev > thr":    (_to_float(vals["ADX_prev"]) is not None) and (_to_float(vals["ADX_prev"]) > ADX_THRESHOLD),
                        "ADX_slope_prev > 0": (_to_float(vals["ADX_slope_prev"]) is not None) and (_to_float(vals["ADX_slope_prev"]) > 0),
                        "CMO_prev > +thr":   (_to_float(vals["CMO_prev"]) is not None) and (_to_float(vals["CMO_prev"]) > CMO_THRESHOLD),
                        "CMO_prev < -thr":   (_to_float(vals["CMO_prev"]) is not None) and (_to_float(vals["CMO_prev"]) < -CMO_THRESHOLD),
                    }
                    passing = [k for k, v in gates.items() if bool(v)]
                    reason = " / ".join(passing) if passing else "No gate satisfied"

                    print(
                        f"{last_iso}: No entry (dir=0). "
                        f"vals={vals_str} thr={{'ADX': {ADX_THRESHOLD}, 'CMO': {CMO_THRESHOLD}}} "
                        f"reason={reason} ATR={atr:.2f}"
                    )
                else:
                    print(f"{last_iso}: No entry (dir=0, ATR={atr:.2f}).")

                time.sleep(POLL_SECONDS)
                continue

            # ---- Daily risk guard ----
            equity = get_equity(trading)

            update_day_start_equity_if_new_day(datetime.now(timezone.utc), equity)
            if should_pause_trading(equity):
                log_event("daily loss guard triggered; skipping entries")
                time.sleep(POLL_SECONDS)
                continue

            # ---- Sizing ----
            price = close

            # Volatility clamp: skip if market too wild
            if (atr / price) > VOL_SPIKE_CAP:
                print(f"{last_iso}: Skip entry (ATR spike {atr/price:.4%} > cap {VOL_SPIKE_CAP:.2%})")
                time.sleep(POLL_SECONDS)
                continue

            # Momentum-based size scaling (uses CMO_prev)
            cmo_prev = float(row.get("CMO_prev", 0.0))
            cmo_thr = max(10, CMO_THRESHOLD)     # avoid being too strict
            raw_mult = min(abs(cmo_prev) / cmo_thr, 1.0)      # 0..1
            risk_mult = max(raw_mult, CMO_SIZE_FLOOR)     # enforce a floor

            # Base size from volatility targeting
            base_qty = atr_position_size(equity, atr, close)

            # Final size with scaling and cap
            qty = min(base_qty * risk_mult, MAX_QTY)

            if qty <= 0:
                print(f"{last_iso}: No entry (qty<=0). ATR={atr:.2f}, equity={equity:.2f}")
                time.sleep(POLL_SECONDS)
                continue

            # ---- Execution ----
            flatten_if_opposite(trading, SYMBOL, entry_dir)

            order = submit_bracket_market(
                trading,
                SYMBOL,
                entry_dir,
                qty,
                close,
                atr
            )
            side_txt = "LONG" if entry_dir == 1 else "SHORT"
            oid = getattr(order, "id", None)
            print(f"{last_iso}: Submitted {side_txt} qty={qty} close≈{close:.2f} ATR={atr:.2f} -> {oid}")
            log_order(SYMBOL, side_txt, qty, close, atr, oid)

        except KeyboardInterrupt:
            log_event("keyboard interrupt -> exiting")
            print("Exiting.")
            break
        except Exception as e:
            log_event(f"ERROR: {e}")
            print("EXCEPTION ->", e)
            traceback.print_exc()
        finally:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
