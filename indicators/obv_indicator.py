#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: On Balance Volume
# ============================================================
"""

def obv_indicator(
    df: pd.DataFrame,
    obv_ma_length: int = 20,
    obv_smooth: str = "EMA",
    divergence_window: int = 20
) -> pd.DataFrame:
    """
                  code  open  high   low  close      volume        amount          obv        obv_ma  obv_divergence
    date
    2026-02-26  600516  5.96  6.00  5.86   5.96   741331.30  4.405121e+08   6618437.11  5.405143e+06           False
    2026-02-27  600516  5.94  6.42  5.90   6.31  2126678.69  1.321854e+09   8745115.80  5.723235e+06           False
    2026-03-02  600516  6.21  6.59  6.13   6.52  2364410.68  1.506674e+09  11109526.48  6.236215e+06           True
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    direction = np.sign(df['close'].diff())
    direction.iloc[0] = 0

    df['obv'] = (direction * df['volume']).cumsum()

    smooth = obv_smooth.upper()

    if smooth == "SMA":
        df['obv_ma'] = df['obv'].rolling(obv_ma_length).mean()

    elif smooth == "EMA":
        df['obv_ma'] = df['obv'].ewm(span=obv_ma_length, adjust=False).mean()

    elif smooth == "WMA":
        weights = np.arange(1, obv_ma_length + 1)
        df['obv_ma'] = df['obv'].rolling(obv_ma_length).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    elif smooth == "RMA":
        df['obv_ma'] = df['obv'].ewm(alpha=1 / obv_ma_length, adjust=False).mean()

    else:
        df['obv_ma'] = np.nan

    w = divergence_window
    prev_close_min = df['close'].shift(1).rolling(w).min()
    prev_obv_min   = df['obv'].shift(1).rolling(w).min()

    price_new_low   = df['close'] <= prev_close_min
    obv_not_new_low = df['obv']   >  prev_obv_min

    df['obv_divergence'] = price_new_low & obv_not_new_low

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(obv_indicator, symbol="600516", start_date="20250101", end_date="20260516")