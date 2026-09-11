#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: KDJ
# ============================================================
"""

def kdj_indicator(
    df: pd.DataFrame,
    kdj_length: int = 9,
    kdj_signal: int = 3,
) -> pd.DataFrame:
    """
                  code  open  high   low  close      volume        amount      kdj_k      kdj_d       kdj_j
    date
    2025-11-13  600516  6.35  6.79  6.26   6.64  3029586.00  1.998156e+09  66.152504  66.275377   65.906757
    2025-11-14  600516  6.61  6.68  6.42   6.43  1825514.00  1.188888e+09  59.867435  64.139396   51.323512
    2025-11-17  600516  6.35  6.46  6.25   6.38  1245315.00  7.885375e+08  53.996130  60.758308   40.471776
    2025-11-18  600516  6.31  6.75  6.28   6.51  2425584.00  1.577879e+09  56.185214  59.233943   50.087755
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    lowest_low   = df['low'].rolling(kdj_length).min()
    highest_high = df['high'].rolling(kdj_length).max()

    hl_diff = highest_high - lowest_low
    rsv = np.where(
        hl_diff == 0,
        50.0,
        (df['close'] - lowest_low) / hl_diff * 100
    )
    rsv = pd.Series(rsv, index=df.index)

    alpha = 1 / kdj_signal

    df['kdj_k'] = rsv.ewm(alpha=alpha, adjust=False).mean()
    df['kdj_d'] = df['kdj_k'].ewm(alpha=alpha, adjust=False).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(kdj_indicator, symbol="600516", start_date="20250101", end_date="20260516")