#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: T3 Moving Average
# ============================================================
"""

def tma_indicator(
    df: pd.DataFrame,
    tma_fast_length: int = 5,
    tma_slow_length: int = 8,
    tma_vfactor: float = 0.618
) -> pd.DataFrame:
    """
                  code       open       high        low      close      volume        amount  turnover_rate    t3_fast    t3_slow t3_signal t3_trend
    date
    2026-02-05  300121  13.180000  13.250000  12.850000  12.880000    79167.00  1.029125e+08         1.8438  13.216052  13.247044      sell     bear
    2026-02-06  300121  12.800000  13.330000  12.730000  13.170000    91865.73  1.207159e+08         2.1396  13.110942  13.267229        no     bear
    2026-02-09  300121  13.330000  13.500000  13.220000  13.300000    66636.00  8.883096e+07         1.5520  13.072233  13.282025        no     bear
    2026-02-24  300121  13.200000  13.400000  13.020000  13.390000    78459.00  1.041765e+08         1.8274  13.177994  13.296270        no     bear
    2026-02-25  300121  13.380000  13.840000  13.310000  13.740000   111661.11  1.526326e+08         2.6006  13.273152  13.293067        no     bear
    2026-02-26  300121  13.730000  13.960000  13.600000  13.860000    91345.50  1.256143e+08         2.1275  13.418943  13.292021       buy     bull
    2026-02-27  300121  13.840000  13.970000  13.690000  13.890000    84972.50  1.177061e+08         1.9791  13.579421  13.294514        no     bull
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    def _gd(series, length, vol_factor):
        ema1 = series.ewm(span=length, adjust=False).mean()
        ema2 = ema1.ewm(span=length, adjust=False).mean()
        return ema1 * (1 + vol_factor) - ema2 * vol_factor

    def _t3(series, length, vol_factor):
        gd1 = _gd(series, length, vol_factor)
        gd2 = _gd(gd1, length, vol_factor)
        gd3 = _gd(gd2, length, vol_factor)
        return gd3

    df['t3_fast'] = _t3(df['close'], tma_fast_length, tma_vfactor)
    df['t3_slow'] = _t3(df['close'], tma_slow_length, tma_vfactor)

    df['t3_signal'] = "no"

    cross_up = (df['t3_fast'] > df['t3_slow']) & (df['t3_fast'].shift(1) <= df['t3_slow'].shift(1))
    cross_down = (df['t3_fast'] < df['t3_slow']) & (df['t3_fast'].shift(1) >= df['t3_slow'].shift(1))

    df.loc[cross_up, 't3_signal'] = "buy"
    df.loc[cross_down, 't3_signal'] = "sell"

    df['t3_trend'] = np.where(df['t3_fast'] > df['t3_slow'], "bull", "bear")

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(tma_indicator, symbol="600516", start_date="20250101", end_date="20260516")