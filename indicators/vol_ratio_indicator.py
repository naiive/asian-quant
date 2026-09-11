#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: Volume Ratio And Turnover
# ============================================================
"""

def vol_ratio_indicator(
    df: pd.DataFrame,
    vol_ma_length: int = 20,
    shrink_threshold: float = 0.7,
    turnover_ref_length: int = 60,
    turnover_low_pct: float = 0.2
) -> pd.DataFrame:
    """
                  code  open  high   low  close      volume        amount  turnover_rate        vol_ma  vol_ratio  vol_shrink  turnover_pct  vol_dried_up
    date
    2026-03-04  600516  6.16  6.36  6.11   6.25   950616.40  5.933256e+08         2.3612  9.499117e+05   1.000742       False      0.783333         False
    2026-03-05  600516  6.30  6.88  6.28   6.88  4249668.70  2.873642e+09        10.5556  1.090386e+06   3.897399       False      1.000000         False
    2026-03-06  600516  6.77  6.88  6.62   6.73  2608595.62  1.747505e+09         6.4794  1.172389e+06   2.225026       False      0.983333         False
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    df['vol_ma']    = df['volume'].rolling(vol_ma_length).mean()
    df['vol_ratio'] = np.where(
        df['vol_ma'] == 0,
        np.nan,
        df['volume'] / df['vol_ma']
    )

    df['vol_shrink'] = df['vol_ratio'] < shrink_threshold

    if 'turnover_rate' in df.columns:
        df['turnover_pct'] = df['turnover_rate'].rolling(turnover_ref_length).rank(pct=True)

        df['vol_dried_up'] = (
            df['vol_shrink'] &
            (df['turnover_pct'] < turnover_low_pct)
        )
    else:
        df['turnover_pct'] = np.nan
        df['vol_dried_up'] = df['vol_shrink']

    return df

if __name__ == '__main__':
    from core.util.func import debug_indicator
    debug_indicator(vol_ratio_indicator, symbol="600516", start_date="20250101", end_date="20260516")