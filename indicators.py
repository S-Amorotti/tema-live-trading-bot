import numpy as np
import pandas as pd


def tema(series: pd.Series, window: int) -> pd.Series:
    ema1 = series.ewm(span=window, adjust=False).mean()
    ema2 = ema1.ewm(span=window, adjust=False).mean()
    ema3 = ema2.ewm(span=window, adjust=False).mean()
    return 3 * (ema1 - ema2) + ema3


def compute_cmo(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0).rolling(window).sum()
    down = (-delta.clip(upper=0)).rolling(window).sum()
    denom = (up + down).replace(0, np.nan)
    cmo = 100 * (up - down) / denom
    return cmo.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def compute_adx(df: pd.DataFrame, window: int = 14) -> pd.Series:
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    plus_dm = plus_dm.where(plus_dm > 0, 0.0)
    minus_dm = minus_dm.where(minus_dm > 0, 0.0)

    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)

    tr14 = tr.rolling(window).sum().replace(0, np.nan)
    plus_di = 100 * plus_dm.rolling(window).sum() / tr14
    minus_di = 100 * minus_dm.rolling(window).sum() / tr14
    denom = (plus_di + minus_di).replace(0, np.nan)

    dx = ((plus_di - minus_di).abs() / denom) * 100
    return dx.rolling(window).mean().fillna(0.0)


def compute_adx_wilder(ohlc: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    Wilder's ADX computed from columns: high, low, close.
    Returns a float Series (same index as input) with NaNs for the warmup,
    then proper ADX values. No post-fill with zeros.
    """
    high = ohlc["high"].astype(float)
    low = ohlc["low"].astype(float)
    close = ohlc["close"].astype(float)

    # True Range
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    # Directional Movements
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where(
        (up_move > down_move) & (up_move > 0),
        up_move, 0.0
    )
    minus_dm = np.where(
        (down_move > up_move) & (down_move > 0),
        down_move, 0.0
    )
    plus_dm = pd.Series(plus_dm, index=ohlc.index)
    minus_dm = pd.Series(minus_dm, index=ohlc.index)

    # Wilder smoothing (RMA) helper
    def rma(x: pd.Series, n: int) -> pd.Series:
        """
        Wilder's RMA with guard for short series.
        Returns NaN until at least n points are present.
        """
        x = x.astype(float)

        if len(x) < n:
            # not enough data yet
            return pd.Series(np.nan, index=x.index)

        alpha = 1.0 / n
        r = x.ewm(alpha=alpha, adjust=False).mean()

        # Seed with the simple mean of the first n values
        seed = x.iloc[:n].mean()
        r.iloc[n-1] = seed

        return r

    atr = rma(tr, window)
    plus_di = 100.0 * rma(plus_dm, window) / atr
    minus_di = 100.0 * rma(minus_dm, window) / atr

    dx = 100.0 * (
        plus_di - minus_di
    ).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = rma(dx, window)

    return adx
