#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: Support And Resistance Levels With Breaks
# ============================================================
"""

def support_resistance_indicator(
    df: pd.DataFrame,
    left_bars: int = 10,
    right_bars: int = 10
):
    """
                  code  open  high   low  close      volume        amount  turnover_rate  srb_res  srb_sup    srb_lab
    date
    2026-03-24  600516  5.80  5.85  5.63   5.81   889004.57  5.112547e+08         2.2082     6.17     5.41        sup
    2026-03-25  600516  5.84  5.88  5.77   5.83   837299.73  4.877241e+08         2.0797     6.17     5.41         no
    2026-03-26  600516  5.80  5.95  5.70   5.73   766087.63  4.454817e+08         1.9029     7.29     5.41         no
    2026-03-27  600516  5.62  5.86  5.61   5.80   640221.82  3.692913e+08         1.5902     7.29     5.41        res
    2026-03-30  600516  5.75  5.78  5.58   5.70   598552.26  3.391753e+08         1.4867     7.29     5.41         no
    2026-03-31  600516  5.70  5.79  5.60   5.70   750875.12  4.276050e+08         1.8651     7.29     5.41         no
    2026-04-01  600516  5.76  5.79  5.67   5.72   497406.84  2.844085e+08         1.2355     7.29     5.41         no
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    window = left_bars + right_bars + 1

    def is_pivot_high(x):
        mid_val = x[left_bars]
        left  = x[:left_bars]
        right = x[left_bars + 1:]
        if np.all(mid_val >= left) and np.all(mid_val > right):
            return mid_val
        return np.nan

    def is_pivot_low(x):
        mid_val = x[left_bars]
        left  = x[:left_bars]
        right = x[left_bars + 1:]
        if np.all(mid_val <= left) and np.all(mid_val < right):
            return mid_val
        return np.nan

    raw_res = df['high'].rolling(window).apply(is_pivot_high, raw=True)
    raw_sup = df['low'].rolling(window).apply(is_pivot_low, raw=True)

    df['srb_res'] = raw_res.ffill()
    df['srb_sup'] = raw_sup.ffill()

    pivot_high_pos = raw_res.notna().shift(-right_bars).fillna(False).astype(bool)
    pivot_low_pos = raw_sup.notna().shift(-right_bars).fillna(False).astype(bool)

    df['srb_lab'] = 'no'
    df.loc[pivot_low_pos,  'srb_lab'] = 'sup'
    df.loc[pivot_high_pos, 'srb_lab'] = 'res'

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(support_resistance_indicator, symbol="600516", start_date="20250101", end_date="20260516")