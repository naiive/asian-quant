#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

from conf.config import SYSTEM_CONFIG

"""
# ============================================================
# Indicator: Anchored VWAP
# ============================================================
"""

def anchored_vwap_indicator(
    df: pd.DataFrame,
    anchor_date: str = SYSTEM_CONFIG.get("ANCHOR_DATE")
) -> pd.DataFrame:
    """
                  code   open   high    low  close      volume        amount     avwap  avwap_bias
    date
    2026-01-29  300086  10.18  10.20   9.89   9.92   300131.35  3.000922e+08  9.140429    8.528829
    2026-01-30  300086   9.86  10.75   9.83  10.14   443437.77  4.614855e+08  9.144887   10.881631
    2026-02-02  300086   9.76   9.76   9.24   9.39   370410.99  3.514420e+08  9.145962    2.668258
    2026-02-03  300086   9.45   9.51   9.15   9.42   255601.80  2.380891e+08  9.146460    2.990670
    2026-02-04  300086   9.39   9.65   9.32   9.57   262918.49  2.502353e+08  9.147334    4.620641
    2026-02-05  300086   9.46   9.97   9.43   9.65   334095.00  3.253980e+08  9.148954    5.476540
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3

    df['pv'] = df['typical_price'] * df['volume']

    anchor_ts = pd.to_datetime(anchor_date)
    mask = df.index >= anchor_ts

    df['avwap'] = np.nan
    df['avwap_bias'] = np.nan

    if mask.any():
        cum_pv = df.loc[mask, 'pv'].cumsum()
        cum_vol = df.loc[mask, 'volume'].cumsum()
        df.loc[mask, 'avwap'] = (cum_pv / cum_vol).round(2)
        bias = ((df.loc[mask, 'close'] - df.loc[mask, 'avwap']) / df.loc[mask, 'avwap']) * 100
        df.loc[mask, 'avwap_bias'] = bias.round(2)

    df.drop(columns=['typical_price', 'pv'], inplace=True)

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(anchored_vwap_indicator, symbol="600516", start_date="20250101", end_date="20260516")