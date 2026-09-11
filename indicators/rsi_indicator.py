#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: Relative Strength Index
# ============================================================
"""

def rsi_indicator(
        df: pd.DataFrame,
        rsi_length: int = 14,
        rsi_ma_length: int = 14,
        rsi_smooth: str = "SMA"
) -> pd.DataFrame:
    """
              code  open  high   low  close     volume        amount        rsi     rsi_ma
    date
    2025-12-17  600628  8.22  8.31  7.99   8.08   478911.0  3.907951e+08  59.679532  55.356665
    2025-12-18  600628  8.00  8.89  7.99   8.89   860952.0  7.394343e+08  72.516204  56.654285
    2025-12-19  600628  9.00  9.77  8.88   9.11  1218309.0  1.129386e+09  74.857507  58.154115
    2025-12-22  600628  9.11  9.18  8.78   8.80   731235.0  6.519696e+08  66.288286  58.357743
    2025-12-23  600628  8.81  8.85  8.50   8.60   549400.0  4.730309e+08  61.404473  58.357782
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    change = df['close'].diff()

    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    alpha = 1 / rsi_length
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    rsi = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    df["rsi"] = np.where(avg_loss == 0, 100, np.where(avg_gain == 0, 0, rsi))

    rsi_smooth = rsi_smooth.upper()

    if rsi_smooth == "SMA":
        df["rsi_ma"] = df["rsi"].rolling(rsi_ma_length).mean()

    elif rsi_smooth == "EMA":
        df["rsi_ma"] = df["rsi"].ewm(span=rsi_ma_length, adjust=False).mean()

    elif rsi_smooth == "WMA":
        weights = np.arange(1, rsi_ma_length + 1)
        df["rsi_ma"] = df["rsi"].rolling(rsi_ma_length).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    elif rsi_smooth == "RMA":
        df["rsi_ma"] = df["rsi"].ewm(alpha=1 / rsi_ma_length, adjust=False).mean()

    else:
        df["rsi_ma"] = np.nan

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(rsi_indicator, symbol="600516", start_date="20250101", end_date="20260516")