#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: ADX And DI
# ============================================================
"""

def wilder_smoothing(series, length):
    values = series.values
    smoothed = np.empty_like(values)
    smoothed.fill(np.nan)

    smoothed[length - 1] = np.sum(values[:length])

    for i in range(length, len(values)):
        smoothed[i] = smoothed[i - 1] - (smoothed[i - 1] / length) + values[i]

    return pd.Series(smoothed, index=series.index)

def adx_indicator(
    df: pd.DataFrame,
    adx_length: int = 14,
    adx_threshold: int = 25
) -> pd.DataFrame:
    """
    code          date   open   high    low  close      volume        amount   adx_plus  adx_minus        adx  adx_threshold
    600218  2024-02-04   7.81   7.90   7.69   7.80   6532800.0  5.111882e+07        NaN        NaN        NaN  25
    600218  2025-02-05   7.62   7.70   7.54   7.67   6697900.0  5.131817e+07  20.923897  23.944273   6.061578  25
    600218  2025-02-06   7.64   7.76   7.62   7.76   7486197.0  5.821225e+07  21.635697  23.167209   4.484860  25
    600218  2025-02-07   7.78   7.99   7.76   7.90   9639047.0  7.676530e+07  25.890815  21.909249   4.198591  25
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    high_low = df['high'] - df['low']
    high_prev_close = np.abs(df['high'] - df['close'].shift(1))
    low_prev_close = np.abs(df['low'] - df['close'].shift(1))

    df['true_range'] = high_low.combine(high_prev_close, max).combine(low_prev_close, max)

    up_move = df['high'] - df['high'].shift(1)
    down_move = df['low'].shift(1) - df['low']

    df['adx_plus'] = np.where((up_move > down_move) & (up_move > 0), up_move, 0)

    df['adx_minus'] = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    df['smoothed_tr'] = wilder_smoothing(df['true_range'], adx_length)
    df['smoothed_dm_plus'] = wilder_smoothing(df['adx_plus'], adx_length)
    df['smoothed_dm_minus'] = wilder_smoothing(df['adx_minus'], adx_length)

    df['adx_plus'] = (df['smoothed_dm_plus'] / df['smoothed_tr']) * 100
    df['adx_minus'] = (df['smoothed_dm_minus'] / df['smoothed_tr']) * 100

    sum_di = df['adx_plus'] + df['adx_minus']
    df['dx'] = np.where(sum_di != 0, np.abs(df['adx_plus'] - df['adx_minus']) / sum_di * 100, 0)

    df['adx'] = df['dx'].rolling(window=adx_length).mean()
    df['adx_threshold'] = adx_threshold

    df.drop(columns=['true_range', 'smoothed_tr', 'smoothed_dm_plus', 'smoothed_dm_minus', 'dx'], inplace=True)

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(adx_indicator, symbol="600516", start_date="20250101", end_date="20260516")