#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: Boom Hunter Pro
# ============================================================
"""

def boo_indicator(
    df: pd.DataFrame,
    lp_period: int = 6,
    k1: float = 0.0,
    k2: float = 0.3,
    lp_period2: int = 27,
    k12: float = 0.8,
    k22: float = 0.3,
    esize: int = 60,
    ey: int = 50,
    trigno: int = 2,
    left_bars: int = 1,
    right_bars: int = 1,
    left_bars_support: int = 5,
    n1: int = 9,
    n2: int = 6
) -> pd.DataFrame:
    """
                      code   open   high    low  close    volume        amount    boo_signal pressure_signal  pressure_count      q1      q2 q_cross
    date
    2024-01-12  002373  10.09  10.09   9.94   9.94   88991.0  8.928018e+07   long yellow           green               3   -7.53   -8.73    gold
    2024-01-24  002373   9.45   9.70   9.00   9.49  366946.0  3.451679e+08     long lime           green              11    0.21   -4.86    gold
    2024-04-18  002373   9.70  10.00   9.65   9.85  205830.0  2.040000e+08  continuation           green               6   26.96   23.50    gold
    2025-01-08  002373   9.03   9.05   8.62   8.91  228945.0  2.026730e+08   long yellow           green               3   -7.50   -8.72    gold
    2025-02-18  002373  10.92  11.02  10.39  10.43  666913.0  7.116313e+08         short             red               3  102.98  104.13   death
    2025-04-10  002373   8.29   8.46   8.25   8.26  233298.0  1.945528e+08   long yellow           green              13   -6.91   -8.43    gold
    2025-04-18  002373   8.17   8.25   8.08   8.22  104759.0  8.548911e+07     long gray           green              19   20.01   19.26    gold
    2025-06-24  002373   8.99   9.20   8.99   9.15  222951.0  2.037284e+08  continuation           green               5   43.23   39.04    gold
    2025-08-11  002373  11.70  11.92  11.65  11.77  395591.0  4.655137e+08         short             red               4  101.54  104.55   death
    2025-09-23  002373  10.76  11.16  10.25  11.15  719924.0  7.770519e+08     long gray              no               0   27.18   21.55    gold
    2025-11-26  002373  11.66  11.98  11.56  11.62  747517.0  8.772677e+08  continuation              no               0   65.13   49.20      no
    2025-12-12  002373  10.54  10.80  10.39  10.80  445775.0  4.718548e+08     long gray           green               3    7.43    6.86    gold
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    hlc3 = (high + low + close) / 3
    n = len(close)

    def calculate_quotient(price, period, k_1, k_2):
        pi = 2 * np.arcsin(1)
        alpha1 = (np.cos(0.707 * 2 * pi / 100) + np.sin(0.707 * 2 * pi / 100) - 1) / np.cos(0.707 * 2 * pi / 100)
        hp, filt, peak, x = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
        q1, q2 = np.zeros(n), np.zeros(n)

        for i in range(2, n):
            hp[i] = (1 - alpha1 / 2) ** 2 * (price[i] - 2 * price[i - 1] + price[i - 2]) + 2 * (1 - alpha1) * hp[
                i - 1] - (1 - alpha1) ** 2 * hp[i - 2]
            a1 = np.exp(-1.414 * pi / period)
            b1 = 2 * a1 * np.cos(1.414 * pi / period)
            c2, c3 = b1, -a1 * a1
            c1 = 1 - c2 - c3
            filt[i] = c1 * (hp[i] + hp[i - 1]) / 2 + c2 * filt[i - 1] + c3 * filt[i - 2]
            peak[i] = 0.991 * peak[i - 1]
            if abs(filt[i]) > peak[i]: peak[i] = abs(filt[i])
            if peak[i] != 0: x[i] = filt[i] / peak[i]
            x_clipped = np.clip(x[i], -0.999, 0.999)
            q1[i] = (x_clipped + k_1) / (k_1 * x_clipped + 1)
            q2[i] = (x_clipped + k_2) / (k_2 * x_clipped + 1)
        return q1, q2

    def calculate_pressure(src_series, n1, n2):
        src = pd.Series(src_series)
        esa = src.ewm(span=n1, adjust=False).mean()
        d = (src - esa).abs().ewm(span=n1, adjust=False).mean()
        ci = (src - esa) / (0.025 * d)
        wt1 = ci.ewm(span=n2, adjust=False).mean() + 50
        wt2 = wt1.rolling(window=6).mean()
        return wt2.fillna(50).values

    q1_seq, q2_seq = calculate_quotient(close, lp_period, k1, k2)
    q3_seq, q4_seq = calculate_quotient(close, lp_period2, k12, k22)

    wt2_values = calculate_pressure(hlc3, n1, n2)

    q1_plot = q1_seq * esize + ey
    trigger = pd.Series(q1_plot).rolling(window=trigno).mean().fillna(0).values

    def crossover(arr1, arr2):
        return (arr1 > arr2) & (np.roll(arr1, 1) <= np.roll(arr2, 1))

    def crossunder(arr1, arr2):
        return (arr1 < arr2) & (np.roll(arr1, 1) >= np.roll(arr2, 1))

    def barssince(condition_array):
        indices = np.where(condition_array)[0]
        result = np.full(len(condition_array), 999999)
        for i in range(len(condition_array)):
            valid_indices = indices[indices <= i]
            if len(valid_indices) > 0: result[i] = i - valid_indices[-1]
        return result

    def get_pivot(arr, left, right, types='high'):
        pivot = np.full(len(arr), np.nan)
        for i in range(left, len(arr) - right):
            window = arr[i - left: i + right + 1]
            if types == 'high' and arr[i] == np.max(window):
                pivot[i] = arr[i]
            elif types == 'low' and arr[i] == np.min(window):
                pivot[i] = arr[i]
        return pd.Series(pivot).ffill().bfill().values

    highusepivot = get_pivot(q1_plot, left_bars, right_bars, 'high')
    lowusepivot = get_pivot(q1_plot, left_bars_support, right_bars, 'low')

    warn2_cond = crossover(q1_seq, -0.9)
    warn3_cond = crossunder(q1_seq, 0.9)
    q1_trigger_cross = crossover(q1_plot, trigger)
    q1_trigger_crossunder = crossunder(q1_plot, trigger)

    enter7 = (q3_seq <= -0.9) & q1_trigger_cross
    enter5_pre = (q1_plot <= 0) & q1_trigger_crossunder
    enter5 = (barssince(enter5_pre) <= 5) & q1_trigger_cross
    enter6_pre = (q1_plot <= 20) & q1_trigger_crossunder
    enter6 = (barssince(enter6_pre) <= 11) & q1_trigger_cross
    enter3_pre_crossover20 = crossover(q1_plot, 20)
    enter3 = (q3_seq <= -0.9) & q1_trigger_cross & (barssince(warn2_cond) <= 7) & (q1_plot <= 20) & (barssince(enter3_pre_crossover20) <= 21)

    senter3_pre_crossover80 = crossover(q1_plot, 80)
    senter3 = (q3_seq >= -0.9) & crossunder(q1_plot, trigger) & (barssince(warn3_cond) <= 7) & (q1_plot >= 99) & (barssince(senter3_pre_crossover80) <= 21)

    continuation_cond = np.zeros(n, dtype=bool)
    dbreak_cnt, ubreak_cnt = 0, 0
    for i in range(1, n):
        if q2_seq[i] < -0.9 <= q2_seq[i - 1]: dbreak_cnt, ubreak_cnt = 0, 0
        if q1_plot[i] < lowusepivot[i - 1] <= q1_plot[i - 1]: dbreak_cnt += 1
        if q1_plot[i] > highusepivot[i - 1] >= q1_plot[i - 1]:
            if dbreak_cnt >= 1: ubreak_cnt += 1
            if dbreak_cnt >= 1 and ubreak_cnt <= 1: continuation_cond[i] = True

    signals = np.full(n, 'no', dtype=object)
    signals[senter3] = 'short'
    signals[enter6] = 'long gray'
    signals[enter5] = 'long blue'
    signals[enter7] = 'long yellow'
    signals[enter3] = 'long lime'
    signals[continuation_cond] = 'continuation'
    df['boo_signal'] = signals

    pressure = np.full(n, 'no', dtype=object)
    pressure_count = np.zeros(n, dtype=int)
    green_mask = wt2_values < 20
    red_mask = wt2_values > 80
    pressure[green_mask] = 'green'
    pressure[red_mask] = 'red'

    current_count = 0
    for i in range(n):
        if pressure[i] != 'no':
            if i > 0 and pressure[i] == pressure[i - 1]:
                current_count += 1
            else:
                current_count = 1
        else:
            current_count = 0
        pressure_count[i] = current_count

    df['pressure_signal'] = pressure
    df['pressure_count'] = pressure_count

    df['q1'] = np.round(q1_plot, 2)
    df['q2'] = np.round(trigger, 2)

    q_cross = np.full(n, 'no', dtype=object)
    q_cross[q1_trigger_cross] = 'gold'
    q_cross[q1_trigger_crossunder] = 'death'
    df['q_cross'] = q_cross

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(boo_indicator, symbol="600516", start_date="20250101", end_date="20260516")