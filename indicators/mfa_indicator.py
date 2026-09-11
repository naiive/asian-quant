#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: Main Force Accumulation
# ============================================================
"""

def mfa_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """
                  code   open   high    low  close     volume        amount  turnover_rate  mfa_value mfa_color  mfa_streak  mfa_all  mfa_max_ratio
    date
    2026-01-20  605299  12.00  12.03  11.75  11.85   89053.00  1.057627e+08         2.1800       0.00        no          52       52         0.0000
    2026-01-21  605299  12.10  13.04  11.75  13.04  254523.00  3.147416e+08         6.2200       0.00        no          53       53         0.0000
    2026-01-22  605299  13.15  13.35  12.81  13.03  476913.00  6.214908e+08        11.6500       0.00        no          54       54         0.0000
    2026-01-23  605299  12.88  13.02  12.69  12.85  269720.00  3.462593e+08         6.5900       0.00        no          55       55         0.0000
    2026-01-26  605299  12.47  12.47  11.57  11.57  182355.00  2.158404e+08         4.4561       0.00        no          56       56         0.0000
    2026-01-27  605299  11.20  11.63  10.92  11.20  230443.00  2.578143e+08         5.6312       7.12       red           1        1         0.2293
    2026-01-28  605299  11.21  11.46  10.99  10.99  153483.00  1.711231e+08         3.7506       3.56     green           1        2         0.2293
    2026-01-29  605299  10.91  11.69  10.85  11.20  236126.21  2.673381e+08         5.7701       9.03       red           1        3         0.2908
    2026-01-30  605299  11.11  11.45  11.11  11.27  159605.99  1.804726e+08         3.9002       4.51     green           1        4         0.2908
    2026-02-02  605299  11.17  11.73  11.17  11.25  130369.99  1.492209e+08         3.1858       2.26     green           2        5         0.2908
    2026-02-03  605299  11.30  11.56  11.24  11.56  111007.00  1.267148e+08         2.7126       1.13     green           3        6         0.2908
    2026-02-04  605299  11.49  11.74  11.48  11.68   92681.00  1.077727e+08         2.2648       0.56     green           4        7         0.2908
    2026-02-05  605299  11.62  12.43  11.58  12.11  194264.00  2.349014e+08         4.7471       0.28     green           5        8         0.2908
    2026-02-06  605299  12.00  12.16  11.70  11.87  145287.00  1.731880e+08         3.5503       0.14     green           6        9         0.2908
    2026-02-09  605299  11.80  12.07  11.76  12.06   96997.00  1.159521e+08         2.3703       0.07     green           7       10         0.2908
    2026-02-10  605299  12.02  12.48  12.00  12.30  129582.01  1.588274e+08         3.1665       0.04     green           8       11         0.2908
    2026-02-11  605299  12.30  12.31  12.04  12.11   63008.99  7.655184e+07         1.5397       0.02     green           9       12         0.2908
    2026-02-12  605299  12.11  12.18  12.02  12.02   66534.99  8.044610e+07         1.6259       0.01     green          10       13         0.2908
    2026-02-13  605299  11.98  12.27  11.98  12.10   75300.99  9.167783e+07         1.8401       0.00     green          11       14         0.2908
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    def _sma_ta(series: pd.Series, n: int, m: int = 1) -> pd.Series:
        alpha = m / n
        return series.ewm(alpha=alpha, adjust=False).mean()

    var1_base = (df['low'] + df['open'] + df['close'] + df['high']) / 4
    var1 = var1_base.shift(1)

    low_minus_var1 = df['low'] - var1
    numerator = _sma_ta(low_minus_var1.abs(), 13, 1)
    denominator = _sma_ta(low_minus_var1.clip(lower=0), 10, 1)

    var2 = numerator / denominator.replace(0, np.nan)
    var2 = var2.fillna(0)

    var3 = var2.ewm(span=10, adjust=False).mean()
    var4 = df['low'].rolling(window=33, min_periods=1).min()

    mfa_condition = np.where(df['low'] <= var4, var3, 0)
    mfa_series = pd.Series(mfa_condition, index=df.index)
    var5 = mfa_series.ewm(span=3, adjust=False).mean()

    df['mfa_value'] = var5.round(2)
    df['mfa_color'] = "no"

    threshold = 0.01
    mfa_red = (df['mfa_value'] > df['mfa_value'].shift(1)) & (df['mfa_value'] >= threshold)
    mfa_green = (df['mfa_value'] < df['mfa_value'].shift(1)) & (df['mfa_value'].shift(1) >= threshold)

    df.loc[mfa_red, 'mfa_color'] = "red"
    df.loc[mfa_green, 'mfa_color'] = "green"

    color_changed = df['mfa_color'] != df['mfa_color'].shift(1)
    color_groups = color_changed.cumsum()
    df['mfa_streak'] = df.groupby(color_groups).cumcount() + 1

    is_no = df['mfa_color'] == "no"
    status_changed = is_no != is_no.shift(1)
    status_groups = status_changed.cumsum()

    raw_streak = df.groupby(status_groups).cumcount() + 1

    df['mfa_all'] = np.where(is_no, raw_streak, raw_streak)

    group_max = df['mfa_value'].groupby(status_groups).cummax()

    global_max = df['mfa_value'].cummax()

    df['mfa_max_ratio'] = (group_max / global_max.replace(0, np.nan)).fillna(0).round(4)

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(mfa_indicator, symbol="605299", start_date="20250101", end_date="20260516")