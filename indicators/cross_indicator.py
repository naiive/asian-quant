#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: WaveTrend With Crosses
# ============================================================
"""

def cross_indicator(
    df: pd.DataFrame,
    channel_length: int = 10,
    average_length: int = 21,
    sma_length: int = 4,
    ob_level1: int = 60,
    ob_level2: int = 53,
    os_level1: int = -60,
    os_level2: int = -53
) -> pd.DataFrame:
    """
                  code  open  high   low  close     volume        amount   wtc_green     wtc_red  wtc_value wtc_signal  wtc_obLevel1  wtc_obLevel2  wtc_osLevel1  wtc_osLevel2
    date
    2025-12-31  600516  5.75  5.78  5.65   5.69   446131.0  2.542247e+08  -29.592649  -29.817095   0.224446         no            60            53           -60           -53
    2026-01-05  600516  5.67  5.70  5.63   5.69   678866.0  3.851948e+08  -32.778757  -29.622028  -3.156729        red            60            53           -60           -53
    2026-01-06  600516  5.70  5.90  5.69   5.89   897114.0  5.243539e+08  -23.910697  -28.520262   4.609564      green            60            53           -60           -53
    2026-01-07  600516  5.93  5.99  5.85   5.89   741927.0  4.381912e+08  -12.377619  -24.664931  12.287312         no            60            53           -60           -53
    2026-01-08  600516  5.88  5.97  5.84   5.92   646235.0  3.818428e+08   -3.944827  -18.252975  14.308148         no            60            53           -60           -53
    2026-01-09  600516  5.93  6.06  5.90   6.04  1158201.0  6.941459e+08    6.154626   -8.519629  14.674255         no            60            53           -60           -53
    2026-01-12  600516  6.07  6.16  6.00   6.14  1274284.0  7.737202e+08   16.380915    1.553274  14.827642         no            60            53           -60           -53
    2026-01-13  600516  6.15  6.17  5.95   5.98  1057621.0  6.373995e+08   20.924698    9.878853  11.045845         no            60            53           -60           -53
    2026-01-14  600516  5.96  6.09  5.89   5.96  1066228.0  6.408052e+08   22.020595   16.370209   5.650386         no            60            53           -60           -53
    2026-01-15  600516  5.93  6.02  5.88   5.90   660590.0  3.918022e+08   20.348320   19.918632   0.429688         no            60            53           -60           -53
    2026-01-16  600516  5.92  6.00  5.82   5.90   671535.0  3.958521e+08   17.050760   20.086093  -3.035333        red            60            53           -60           -53
    2026-01-19  600516  5.89  5.98  5.82   5.98   616560.0  3.656526e+08   15.668211   18.771971  -3.103761         no            60            53           -60           -53
    2026-01-20  600516  5.91  5.91  5.53   5.62  1586188.0  8.970064e+08    0.489826   13.389279 -12.899453         no            60            53           -60           -53
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    ap = (df['high'] + df['low'] + df['close']) / 3

    esa = ap.ewm(span=channel_length, adjust=False).mean()

    d = (ap - esa).abs().ewm(span=channel_length, adjust=False).mean()

    ci = (ap - esa) / (0.015 * d)

    wtc_green = ci.ewm(span=average_length, adjust=False).mean()

    wtc_red = wtc_green.rolling(window=sma_length).mean()

    wtc_value = wtc_green - wtc_red

    cross_up = (wtc_green.shift(1) < wtc_red.shift(1)) & (wtc_green > wtc_red)

    cross_down = (wtc_green.shift(1) > wtc_red.shift(1)) & (wtc_green < wtc_red)

    signal = np.where(
        cross_up, "green",
        np.where(cross_down, "red", "no")
    )

    df['wtc_green'] = wtc_green
    df['wtc_red'] = wtc_red
    df['wtc_value'] = wtc_value
    df['wtc_signal'] = signal

    df['wtc_obLevel1'] = ob_level1
    df['wtc_obLevel2'] = ob_level2
    df['wtc_osLevel1'] = os_level1
    df['wtc_osLevel2'] = os_level2

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(cross_indicator, symbol="600516", start_date="20250101", end_date="20260516")
