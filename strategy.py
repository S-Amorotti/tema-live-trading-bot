import numpy as np
import pandas as pd
from indicators import tema, compute_atr, compute_adx_wilder, compute_cmo
from config import ADX_THRESHOLD, CMO_THRESHOLD


def _ensure_ts_col(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure a 'ts' column exists from the DatetimeIndex (whatever its name),
    sorted and tz-aware in UTC.
    """
    x = df.sort_index().copy()

    # Ensure DatetimeIndex and UTC
    if not isinstance(x.index, pd.DatetimeIndex):
        raise TypeError("Expected a DatetimeIndex for OHLC data.")
    if x.index.tz is None:
        x.index = x.index.tz_localize("UTC")
    else:
        x.index = x.index.tz_convert("UTC")

    # Reset index to a column named 'ts' (works for unnamed indexes too)
    try:
        x = x.reset_index(names="ts")
    except TypeError:
        x = x.reset_index()
        x = x.rename(columns={x.columns[0]: "ts"})
    return x


def _mtf_join_4h_onto_1h(
        df_1h: pd.DataFrame, df_4h: pd.DataFrame
        ) -> pd.DataFrame:
    """
    Join 4H features onto the 1H timeline via merge_asof on 'ts'.
    """
    df1 = _ensure_ts_col(df_1h)
    df4 = _ensure_ts_col(df_4h)

    # Prefix 4h columns (avoid collisions with 1h names)
    df4 = df4.rename(columns={c: f"4h_{c}" for c in df4.columns if c != "ts"})

    out = pd.merge_asof(
        df1.sort_values("ts"),
        df4.sort_values("ts"),
        on="ts",
        direction="backward",
        allow_exact_matches=True,
    )
    out = out.set_index("ts").sort_index()
    return out


def compute_signals(df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    one = df_1h.copy()

    # === 1H indicators ===
    one["TEMA10"] = tema(one["close"], 10)
    one["TEMA80"] = tema(one["close"], 80)
    one["ADX"] = compute_adx_wilder(one, window=14)
    one["CMO"] = compute_cmo(one["close"], window=14)
    one["ATR"] = compute_atr(one, window=14)

    # === 4H indicators ===
    four = df_4h.copy()
    four["TEMA20"] = tema(four["close"], 20)
    four["TEMA70"] = tema(four["close"], 70)

    # === Join 4H onto 1H ===
    out = _mtf_join_4h_onto_1h(one, four)

    # Forward-fill 4h fields so a fresh 1h bar
    # isn't NaN before the next 4h close
    for c in ["4h_TEMA20", "4h_TEMA70"]:
        if c in out.columns:
            out[c] = out[c].ffill()

    # === Trend flags (current bar) ===
    out["ShortTrend"] = (out["TEMA10"] > out["TEMA80"]).astype(int)
    out["LongTrend"] = (out["4h_TEMA20"] > out["4h_TEMA70"]).astype(int)

    # === Confirmed values (t-1), then ffill to avoid NaNs on last bar ===
    out["ShortTrend_prev"] = out["ShortTrend"].shift(1)
    out["LongTrend_prev"] = out["LongTrend"].shift(1)
    out["ADX_prev"] = out["ADX"].shift(1)
    out["ADX_slope_prev"] = out["ADX"].diff().shift(1)
    out["CMO_prev"] = out["CMO"].shift(1)

    prev_cols = [
        "ShortTrend_prev",
        "LongTrend_prev",
        "ADX_prev",
        "ADX_slope_prev",
        "CMO_prev"
    ]
    out[prev_cols] = out[prev_cols].ffill()

    # cast prev trend flags to 0/1 (after ffill)
    out["ShortTrend_prev"] = out["ShortTrend_prev"].fillna(0).astype(int)
    out["LongTrend_prev"] = out["LongTrend_prev"].fillna(0).astype(int)

    # === Entry rules (confirmed) ===
    out["long_signal"] = (
        (out["ShortTrend_prev"] == 1) & (out["LongTrend_prev"] == 1) &
        (out["ADX_prev"] > ADX_THRESHOLD) &
        (out["ADX_slope_prev"] > 0) &
        (out["CMO_prev"] > CMO_THRESHOLD)
    )

    out["short_signal"] = (
        (out["ShortTrend_prev"] == 0) & (out["LongTrend_prev"] == 0) &
        (out["ADX_prev"] > ADX_THRESHOLD) &
        (out["ADX_slope_prev"] > 0) &
        (out["CMO_prev"] < -CMO_THRESHOLD)
    )

    out["entry_dir"] = np.where(out["long_signal"], 1,
                                np.where(out["short_signal"], -1, 0))

    return out
