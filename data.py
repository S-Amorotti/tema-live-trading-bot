from datetime import datetime, timedelta, timezone
import pandas as pd
from alpaca.data.historical import (
    CryptoHistoricalDataClient,
    StockHistoricalDataClient
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from config import IS_CRYPTO, LOOKBACK_1H, LOOKBACK_4H


def fetch_bars(
        symbol: str,
        tf: TimeFrame,
        lookback: int,
        is_crypto: bool) -> pd.DataFrame:

    end = datetime.now(timezone.utc)
    # estimate days needed: lookback bars * bar duration
    if tf.amount == 1 and tf.unit.name.lower() == "hour":
        days_back = int((lookback * 1.5) / 24) + 2  # 1h bars
    elif tf.amount == 4 and tf.unit.name.lower() == "hour":
        days_back = int((lookback * 4 * 1.5) / 24) + 2  # 4h bars
    else:
        days_back = 30  # safe fallback

    start = end - timedelta(days=days_back)

    if is_crypto:
        client = CryptoHistoricalDataClient()
        req = CryptoBarsRequest(
            symbol_or_symbols=symbol,   # str avoids MultiIndex
            timeframe=tf,
            start=start,
            end=end,
            feed="us",
        )
        bars = client.get_crypto_bars(req).df
    else:
        client = StockHistoricalDataClient()
        req = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=tf,
            start=start,
            end=end,
        )
        bars = client.get_stock_bars(req).df

    if bars.empty:
        print(
            f"[data] Empty bars for {symbol} tf={tf} (is_crypto={is_crypto})"
        )
        return pd.DataFrame()

    # Flatten MultiIndex
    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.xs(symbol, level=0)

    bars = bars.rename(columns=str.lower)

    if bars.index.tz is None:
        bars.index = bars.index.tz_localize(timezone.utc)
    else:
        bars.index = bars.index.tz_convert(timezone.utc)

    return bars[['open', 'high', 'low', 'close', 'volume']]


def get_1h_and_4h(symbol: str):
    tf1h = TimeFrame(amount=1, unit=TimeFrameUnit.Hour)
    tf4h = TimeFrame(amount=4, unit=TimeFrameUnit.Hour)
    df_1h = fetch_bars(symbol, tf1h, LOOKBACK_1H, IS_CRYPTO)
    df_4h = fetch_bars(symbol, tf4h, LOOKBACK_4H, IS_CRYPTO)
    return df_1h, df_4h
