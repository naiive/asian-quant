#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: UT Bot Alerts
# ============================================================
"""

def utb_indicator(
    df: pd.DataFrame,
    key_value: float = 2,
    atr_period: int = 14,
    use_ha: bool = False
) -> pd.DataFrame:
    """
                  code   open   high    low  close      volume        amount  turnover_rate utb_signal utb_trend
        date
    2025-12-30  600588  12.96  13.23  12.96  13.10   417168.00  5.482072e+08         1.2200       buy     bull
    2025-12-31  600588  13.10  13.35  13.06  13.26   404832.00  5.367386e+08         1.1800        no     bull
    2026-01-05  600588  13.35  13.70  13.21  13.67   690778.00  9.316988e+08         2.0200        no     bull
    2026-01-14  600588  17.65  19.01  17.63  19.01  3472443.00  6.447854e+09        10.1600        no     bull
    2026-01-15  600588  18.61  18.61  17.16  17.50  3879575.00  6.865491e+09        11.3500      sell     bear
    2026-01-16  600588  16.91  17.50  16.00  16.09  2615936.00  4.346110e+09         7.6600        no     bear
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    if use_ha:
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = np.zeros(len(df))
        ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2
        src = ha_close
    else:
        src = df['close']

    high = df['high']
    low = df['low']
    close = df['close']

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / atr_period, min_periods=atr_period, adjust=False).mean()
    n_loss = key_value * atr

    src_arr = src.to_numpy()
    nloss_arr = n_loss.to_numpy()
    stop_arr = np.zeros(len(df))

    for i in range(len(df)):
        if i == 0 or np.isnan(nloss_arr[i]):
            stop_arr[i] = src_arr[i]
            continue
        c, pc, ps, nl = src_arr[i], src_arr[i - 1], stop_arr[i - 1], nloss_arr[i]
        if c > ps and pc > ps:
            stop_arr[i] = max(ps, c - nl)
        elif c < ps and pc < ps:
            stop_arr[i] = min(ps, c + nl)
        elif c > ps:
            stop_arr[i] = c - nl
        else:
            stop_arr[i] = c + nl

    pos_arr = np.zeros(len(df), dtype=int)
    for i in range(1, len(df)):
        if src_arr[i - 1] < stop_arr[i - 1] < src_arr[i]:
            pos_arr[i] = 1
        elif src_arr[i - 1] > stop_arr[i - 1] > src_arr[i]:
            pos_arr[i] = -1
        else:
            pos_arr[i] = pos_arr[i - 1]

    src_s = pd.Series(src_arr, index=df.index)
    stop_s = pd.Series(stop_arr, index=df.index)

    above = (src_s > stop_s) & (src_s.shift(1) <= stop_s.shift(1))
    below = (stop_s > src_s) & (stop_s.shift(1) <= src_s.shift(1))

    utb_signal = pd.Series('no', index=df.index, name='utb_signal')
    utb_signal = utb_signal.mask((src_s > stop_s) & above, 'buy')
    utb_signal = utb_signal.mask((src_s < stop_s) & below, 'sell')

    utb_trend = pd.Series(
        np.where(
            pos_arr == 1, 'bull',
            np.where(
                pos_arr == -1, 'bear',
                np.where(src_arr > stop_arr, 'bull', 'bear')
            )
        ),
        index=df.index,
        name='utb_trend',
    )

    df['utb_signal'] = utb_signal
    df['utb_trend'] = utb_trend

    return df

if __name__ == '__main__':
    from core.util.func import debug_indicator
    debug_indicator(utb_indicator, symbol="600516", start_date="20250101", end_date="20260516")
