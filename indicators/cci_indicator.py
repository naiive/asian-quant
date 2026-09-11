#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: Commodity Channel Index
# ============================================================
"""

def cci_indicator(
    df: pd.DataFrame,
    cci_length: int = 14,
    cci_constant: float = 0.015,
    cci_ma_length: int = 14,
    cci_smooth: str = "None"
) -> pd.DataFrame:
    """
                  code  open  high   low  close      volume        amount         cci      cci_ma
    date
    2026-03-03  600516  6.42  6.53  6.21   6.23  1437971.80  9.088426e+08  146.524302   40.275611
    2026-03-04  600516  6.16  6.36  6.11   6.25   950616.40  5.933256e+08   97.071670   48.711721
    2026-03-05  600516  6.30  6.88  6.28   6.88  4249668.70  2.873642e+09  165.707405   64.875128
    2026-03-06  600516  6.77  6.88  6.62   6.73  2608595.62  1.747505e+09  140.847422   79.621304
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    tp = (df['high'] + df['low'] + df['close']) / 3

    ma = tp.rolling(cci_length).mean()
    md = tp.rolling(cci_length).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )

    df['cci'] = np.where(
        md == 0,
        0.0,
        (tp - ma) / (cci_constant * md)
    )

    smooth = cci_smooth.upper()

    if smooth == "SMA":
        df['cci_ma'] = df['cci'].rolling(cci_ma_length).mean()

    elif smooth == "EMA":
        df['cci_ma'] = df['cci'].ewm(span=cci_ma_length, adjust=False).mean()

    elif smooth == "WMA":
        weights = np.arange(1, cci_ma_length + 1)
        df['cci_ma'] = df['cci'].rolling(cci_ma_length).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    elif smooth == "RMA":
        df['cci_ma'] = df['cci'].ewm(alpha=1 / cci_ma_length, adjust=False).mean()

    else:
        df['cci_ma'] = np.nan

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(cci_indicator, symbol="600516", start_date="20250101", end_date="20260516")