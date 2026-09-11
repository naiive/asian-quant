#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: Stochastic
# ============================================================
"""

def stochastic_indicator(
    df: pd.DataFrame,
    sto_period_k: int = 21,
    sto_smooth_k: int = 3,
    sto_smooth_d: int = 3
) -> pd.DataFrame:
    """
                  code       open       high        low      close      volume        amount    stoch_k    stoch_d stoch_s stoch_div         rsv     stoch_j stoch_kdj
    date
    2025-02-20  300170  21.120696  21.938400  20.661984  21.479688  1776340.27  3.791658e+09  73.580443  72.576672      no        no   72.557793   75.587984     green
    2025-02-21  300170  21.409884  22.815936  20.691900  22.317336  2371236.97  5.151422e+09  75.327553  73.493633     buy       buy   78.821775   78.995395     green
    2025-02-24  300170  21.768876  21.908484  20.741760  20.851452  1535994.85  3.286558e+09  72.838304  73.275190    sell        no   67.859806   71.964533       red
    2025-03-05  300170  18.597780  18.926856  18.139068  18.876996  1026867.78  1.914301e+09  24.952102  38.527614      no      sell   14.654003   -2.198923       red
    2025-03-06  300170  21.439800  22.656384  21.060864  22.656384  2822097.30  6.232689e+09  38.660967  38.572065     buy        no   66.078697   38.838771     green
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    low_min = df['low'].rolling(window=sto_period_k).min()
    high_max = df['high'].rolling(window=sto_period_k).max()
    stoch_raw = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-9)

    df['stoch_k'] = stoch_raw.rolling(window=sto_smooth_k).mean()
    df['stoch_d'] = df['stoch_k'].rolling(window=sto_smooth_d).mean()

    k_cross_over_d = (df['stoch_k'] > df['stoch_d']) & (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1))
    k_cross_under_d = (df['stoch_k'] < df['stoch_d']) & (df['stoch_k'].shift(1) >= df['stoch_d'].shift(1))

    df['stoch_s'] = "no"
    df.loc[k_cross_over_d, 'stoch_s'] = "buy"
    df.loc[k_cross_under_d, 'stoch_s'] = "sell"

    df['stoch_div'] = "no"

    gc_points = df[k_cross_over_d][['close', 'stoch_k']].copy()
    sc_points = df[k_cross_under_d][['close', 'stoch_k']].copy()

    prev_gc_price = gc_points['close'].shift(1).reindex(df.index).ffill()
    prev_gc_k = gc_points['stoch_k'].shift(1).reindex(df.index).ffill()

    prev_sc_price = sc_points['close'].shift(1).reindex(df.index).ffill()
    prev_sc_k = sc_points['stoch_k'].shift(1).reindex(df.index).ffill()

    bull_div = k_cross_over_d & (df['close'] < prev_gc_price) & (df['stoch_k'] > prev_gc_k)
    df.loc[bull_div, 'stoch_div'] = "buy"

    bear_div = k_cross_under_d & (df['close'] > prev_sc_price) & (df['stoch_k'] < prev_sc_k)
    df.loc[bear_div, 'stoch_div'] = "sell"

    low_min = df['low'].rolling(window=sto_period_k).min()
    high_max = df['high'].rolling(window=sto_period_k).max()

    df['rsv'] = 100 * ((df['close'] - low_min) / (high_max - low_min).replace(0, np.inf))
    df['rsv'] = df['rsv'].fillna(0)

    def bcwsma(series, period):
        return series.ewm(alpha=1 / period, adjust=False).mean()

    df['stoch_k'] = bcwsma(df['rsv'], sto_smooth_k)
    df['stoch_d'] = bcwsma(df['stoch_k'], sto_smooth_d)
    df['stoch_j'] = 3 * df['stoch_k'] - 2 * df['stoch_d']

    df['stoch_kdj'] = np.where(df['stoch_j'] > df['stoch_d'], 'green', 'red')

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(stochastic_indicator, symbol="600516", start_date="20250101", end_date="20260516")