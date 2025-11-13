import csv
from datetime import datetime, timezone
from config import ORDER_LOG, EVENT_LOG


def log_event(msg: str):
    ts = datetime.now(timezone.utc).isoformat()
    with open(EVENT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def log_order(
        symbol: str,
        side: str,
        qty: float,
        price: float,
        atr: float,
        order_id: str | None
        ):
    write_header = not ORDER_LOG.exists()
    with open(ORDER_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow([
                "ts_utc",
                "symbol",
                "side",
                "qty",
                "price",
                "atr",
                "order_id"
            ])
        w.writerow([
            datetime.now(timezone.utc).isoformat(),
            symbol,
            side,
            qty,
            price,
            atr,
            order_id or ""
        ])
