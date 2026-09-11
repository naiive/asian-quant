#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: Range Filter
# ============================================================
"""

def rgf_indicator(
    df: pd.DataFrame,
    rgf_per: int = 14,
    rgf_qty: float = 2.5
) -> pd.DataFrame:
    """
                  code   open   high    low  close      volume        amount   rgf     rgf_signal
    date
    2025-01-09  600588   9.81  10.20   9.78  10.13   318640.00  3.196599e+08  10.170000        no
    2025-01-10  600588  10.13  10.19   9.70   9.71   230894.00  2.296333e+08  10.135123      sell
    2025-01-20  600588  10.11  10.17   9.96  10.00   214096.00  2.154514e+08  10.135123        no
    2025-01-23  600588  10.02  10.34   9.90   9.91   330810.00  3.350205e+08  10.135123        no
    2025-01-24  600588   9.80  10.90   9.72  10.90   865720.00  9.145282e+08  10.454791       buy
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    src = df['close'].values
    n = len(src)

    def get_pine_ema(dat, length):
        alpha = 2 / (length + 1)
        ema_arr = np.full(n, np.nan)
        current_ema = np.nan

        for v in range(n):
            val = dat[v]
            if np.isnan(val):
                continue
            if np.isnan(current_ema):
                current_ema = val
            else:
                current_ema = alpha * val + (1 - alpha) * current_ema
            ema_arr[v] = current_ema

        return ema_arr

    abs_diff = np.full(n, np.nan)
    abs_diff[1:] = np.abs(np.diff(src))

    av_range = get_pine_ema(abs_diff, rgf_per)
    wper = (rgf_per * 2) - 1
    r_size = get_pine_ema(av_range, wper) * rgf_qty

    rfilt = np.zeros(n)
    fdir = np.zeros(n, dtype=int)
    last_signal_tracker = 0
    results = ["no"] * n

    rfilt[0] = src[0]

    for i in range(1, n):
        rng = r_size[i]
        curr_src = src[i]
        prev_filt = rfilt[i - 1]

        if np.isnan(rng):
            rfilt[i] = prev_filt
        else:
            if curr_src - rng > prev_filt:
                rfilt[i] = curr_src - rng
            elif curr_src + rng < prev_filt:
                rfilt[i] = curr_src + rng
            else:
                rfilt[i] = prev_filt

        if rfilt[i] > rfilt[i - 1]:
            fdir[i] = 1
        elif rfilt[i] < rfilt[i - 1]:
            fdir[i] = -1
        else:
            fdir[i] = fdir[i - 1]

        if not np.isnan(rng):
            long_cond  = (curr_src > rfilt[i]) and (fdir[i] == 1)
            short_cond = (curr_src < rfilt[i]) and (fdir[i] == -1)

            if long_cond and last_signal_tracker <= 0:
                results[i] = "buy"
                last_signal_tracker = 1
            elif short_cond and last_signal_tracker >= 0:
                results[i] = "sell"
                last_signal_tracker = -1

    df['rgf']   = rfilt
    df['rgf_signal'] = results

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(rgf_indicator, symbol="600516", start_date="20250101", end_date="20260516")