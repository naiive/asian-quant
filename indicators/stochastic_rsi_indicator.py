#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: Stochastic RSI
# ============================================================
"""

def stochastic_rsi_indicator(
    df: pd.DataFrame,
    stoch_length: int = 14,
    smooth_k: int = 3,
    smooth_d: int = 3
) -> pd.DataFrame:
    """
                  code   open   high    low  close     volume        amount        rsi  stochrsi_k  stochrsi_d  stochrsi_r  stochrsi_b
    date
    2026-01-27  003036  16.50  16.51  15.91  16.27   28523.00  4.609196e+07  49.522271   42.463159   68.810022    0.617107           no
    2026-01-28  003036  16.27  16.30  15.85  15.95   31810.81  5.080872e+07  44.413448   17.133296   43.855611    0.390675           no
    2026-01-29  003036  15.85  16.13  15.69  15.82   24927.00  3.959906e+07  42.495480    3.826114   21.140856    0.180982           no
    2026-01-30  003036  15.75  16.00  15.64  15.98   22051.00  3.492893e+07  45.608752    4.788112    8.582507    0.557892           no
    2026-02-02  003036  15.91  16.45  15.87  16.17   41309.78  6.700142e+07  49.130747   14.992938    7.869054    1.905304          yes
    2026-02-03  003036  16.19  16.48  16.09  16.41   31599.00  5.172194e+07  53.248824   31.531235   17.104095    1.843490          yes
    2026-02-04  003036  16.40  16.98  16.33  16.96   56838.00  9.522986e+07  61.033891   55.254602   33.926258    1.628668           no
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    change = df['close'].diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    alpha = 1 / stoch_length
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = np.where(avg_loss == 0, 100, np.where(avg_gain == 0, 0, rsi))
    df['rsi'] = rsi

    stoch_min = df['rsi'].rolling(window=stoch_length).min()
    stoch_max = df['rsi'].rolling(window=stoch_length).max()

    stoch_rsi_raw = 100 * (df['rsi'] - stoch_min) / (stoch_max - stoch_min)

    df['stochrsi_k'] = stoch_rsi_raw.rolling(window=smooth_k).mean()
    df['stochrsi_d'] = df['stochrsi_k'].rolling(window=smooth_d).mean()
    df['stochrsi_r'] = df['stochrsi_k'] / df['stochrsi_d'].replace(0, np.nan)

    k_threshold, d_threshold, r_threshold = 8.0, 4.0, 1.8
    buy_condition = (
        (df['stochrsi_k'] > k_threshold) &
        (df['stochrsi_k'] > df['stochrsi_d']) &
        (df['stochrsi_d'] > d_threshold) &
        (df['stochrsi_r'] > r_threshold)
    )
    df['stochrsi_b'] = np.where(buy_condition, "yes", "no")

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(stochastic_rsi_indicator, symbol="600516", start_date="20250101", end_date="20260516")