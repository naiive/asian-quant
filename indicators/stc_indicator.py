#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: Schaff Trend Cycle
# ============================================================
"""

def stc_indicator(
    df: pd.DataFrame,
    stc_length: int = 12,
    stc_fast_length: int = 26,
    stc_slow_length: int = 50,
    stc_factor: float = 0.5
) -> pd.DataFrame:
    """
                  code   open   high    low  close      volume        amount     stc stc_signal stc_trend
    date
    2025-01-09  600588   9.81  10.20   9.78  10.13   318640.00  3.196599e+08  54.321        no      bull
    2025-01-10  600588  10.13  10.19   9.70   9.71   230894.00  2.296333e+08  48.765      sell      bear
    2025-01-20  600588  10.11  10.17   9.96  10.00   214096.00  2.154514e+08  32.100        no      bear
    2025-01-23  600588  10.02  10.34   9.90   9.91   330810.00  3.350205e+08  22.500        no      bear
    2025-01-24  600588   9.80  10.90   9.72  10.90   865720.00  9.145282e+08  28.900       buy      bull
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    src = df['close'].values
    n = len(src)

    def get_pine_ema(dat: np.ndarray, length: int) -> np.ndarray:
        alpha = 2.0 / (length + 1)
        ema_arr = np.full(n, np.nan)
        current_ema = np.nan
        for x in range(n):
            val = dat[x]
            if np.isnan(val):
                continue
            if np.isnan(current_ema):
                current_ema = val
            else:
                current_ema = alpha * val + (1 - alpha) * current_ema
            ema_arr[x] = current_ema
        return ema_arr

    def rolling_lowest(dat: np.ndarray, length: int) -> np.ndarray:
        result = np.full(n, np.nan)
        for x in range(n):
            start = max(0, x - length + 1)
            window = dat[start: x + 1]
            valid = window[~np.isnan(window)]
            if len(valid) > 0:
                result[x] = np.min(valid)
        return result

    def rolling_highest(dat: np.ndarray, length: int) -> np.ndarray:
        result = np.full(n, np.nan)
        for x in range(n):
            start = max(0, x - length + 1)
            window = dat[start: x + 1]
            valid = window[~np.isnan(window)]
            if len(valid) > 0:
                result[x] = np.max(valid)
        return result

    fast_ma = get_pine_ema(src, stc_fast_length)
    slow_ma = get_pine_ema(src, stc_slow_length)
    macd = fast_ma - slow_ma

    macd_lowest  = rolling_lowest(macd, stc_length)
    macd_highest = rolling_highest(macd, stc_length)

    f1 = np.full(n, np.nan)
    d1 = np.zeros(n)

    for i in range(n):
        macd_range = macd_highest[i] - macd_lowest[i]
        if not np.isnan(macd_range) and macd_range > 0:
            f1[i] = (macd[i] - macd_lowest[i]) / macd_range * 100
        else:
            f1[i] = f1[i - 1] if i > 0 and not np.isnan(f1[i - 1]) else 0.0

        d1[i] = d1[i - 1] + stc_factor * (f1[i] - d1[i - 1]) if i > 0 else f1[i]

    d1_lowest  = rolling_lowest(d1, stc_length)
    d1_highest = rolling_highest(d1, stc_length)

    f2  = np.full(n, np.nan)
    stc = np.zeros(n)

    for i in range(n):
        d1_range = d1_highest[i] - d1_lowest[i]
        if not np.isnan(d1_range) and d1_range > 0:
            f2[i] = (d1[i] - d1_lowest[i]) / d1_range * 100
        else:
            f2[i] = f2[i - 1] if i > 0 and not np.isnan(f2[i - 1]) else 0.0

        stc[i] = stc[i - 1] + stc_factor * (f2[i] - stc[i - 1]) if i > 0 else f2[i]

    trends = ["bear"] * n

    for i in range(1, n):
        if np.isnan(stc[i]) or np.isnan(stc[i - 1]):
            trends[i] = trends[i - 1]
        elif stc[i] > stc[i - 1]:
            trends[i] = "bull"
        else:
            trends[i] = "bear"

    signals = ["no"] * n

    for i in range(1, n):
        if trends[i] == "bull" and trends[i - 1] == "bear":
            signals[i] = "buy"
        elif trends[i] == "bear" and trends[i - 1] == "bull":
            signals[i] = "sell"

    df['stc'] = np.round(stc.astype(float), 4)
    df['stc_signal'] = signals
    df['stc_trend']  = trends

    pd.options.display.float_format = '{:.4f}'.format

    return df


if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(stc_indicator, symbol="600516", start_date="20250101", end_date="20260516")