#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: MACD Histogram Double Divergence
# ============================================================
"""

def macd_divergence_indicator(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    lb_left: int = 2,
    lb_right: int = 2,
    size_factor: float = 0.1,
    size_ratio: float = 1.2,
    max_bars: int = 0
) -> pd.DataFrame:
    """
                  code    open    high     low   close     volume        amount    hist  min_threshold macd_divergence macd_l_date  macd_l_hist macd_r_date  macd_r_hist
    date
    2023-12-04  002352   38.81   39.05   38.25   38.46   100290.0  4.167862e+08  0.1664       0.094165            bear  2023-11-21       0.3864  2023-11-30       0.2509
    2025-12-15  002352   37.20   37.79   37.18   37.41   188234.0  7.066892e+08 -0.0757       0.075713            bull  2025-12-04      -0.1550  2025-12-11      -0.1138
    2026-01-12  002352   39.01   39.17   38.81   39.01   279380.0  1.088650e+09  0.1961       0.084234              no         NaT          NaN         NaT          NaN
    2026-01-15  002352   38.90   39.93   38.88   39.19   474063.0  1.870599e+09  0.1455       0.084454              no         NaT          NaN         NaT          NaN
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    df['hist'] = (macd_line - signal_line).round(4)

    df['min_threshold'] = signal_line.abs().rolling(100).mean() * size_factor

    df['macd_divergence'] = 'no'
    df['macd_l_date'] = pd.NaT
    df['macd_l_hist'] = np.nan
    df['macd_r_date'] = pd.NaT
    df['macd_r_hist'] = np.nan

    bull_left_h = np.nan
    bull_left_p = np.nan
    bull_left_d = pd.NaT

    bear_left_h = np.nan
    bear_left_p = np.nan
    bear_left_d = pd.NaT

    green_count = 0
    red_count = 0

    hist_vals = df['hist'].values
    low_vals = df['low'].values
    high_vals = df['high'].values
    date_vals = df.index.values
    thr_vals = df['min_threshold'].values
    n = len(df)

    for i in range(n):
        if hist_vals[i] > 0:
            green_count += 1
            red_count = 0
        elif hist_vals[i] < 0:
            red_count += 1
            green_count = 0
        else:
            green_count = 0
            red_count = 0

        if green_count > max_bars:
            bull_left_h = np.nan
        if red_count > max_bars:
            bear_left_h = np.nan

        detect_idx = i - lb_right
        if detect_idx < lb_left:
            continue

        center_h = hist_vals[detect_idx]
        thr = thr_vals[detect_idx]

        is_pl = False
        if center_h < 0 and abs(center_h) > thr:
            l_win = hist_vals[detect_idx - lb_left: detect_idx]
            r_win = hist_vals[detect_idx + 1: detect_idx + lb_right + 1]
            if np.all(l_win > center_h) and np.all(r_win > center_h):
                is_pl = True

        if is_pl:
            cur_h = center_h
            cur_p = low_vals[detect_idx]
            cur_d = date_vals[detect_idx]

            if not np.isnan(bull_left_h):
                ratio_ok = abs(bull_left_h / cur_h) >= size_ratio
                price_ok = cur_p <= bull_left_p
                energy_ok = cur_h > bull_left_h

                if ratio_ok and price_ok and energy_ok:
                    df.iloc[i, df.columns.get_loc('macd_divergence')] = 'bull'
                    df.iloc[i, df.columns.get_loc('macd_l_date')] = bull_left_d
                    df.iloc[i, df.columns.get_loc('macd_l_hist')] = bull_left_h
                    df.iloc[i, df.columns.get_loc('macd_r_date')] = cur_d
                    df.iloc[i, df.columns.get_loc('macd_r_hist')] = cur_h

            bull_left_h = cur_h
            bull_left_p = cur_p
            bull_left_d = cur_d
            green_count = 0

        is_ph = False
        if center_h > 0 and abs(center_h) > thr:
            l_win = hist_vals[detect_idx - lb_left: detect_idx]
            r_win = hist_vals[detect_idx + 1: detect_idx + lb_right + 1]
            if np.all(l_win < center_h) and np.all(r_win < center_h):
                is_ph = True

        if is_ph:
            cur_h_bear = center_h
            cur_p_bear = high_vals[detect_idx]
            cur_d_bear = date_vals[detect_idx]

            if not np.isnan(bear_left_h):
                ratio_ok_bear = abs(bear_left_h / cur_h_bear) >= size_ratio
                price_ok_bear = cur_p_bear >= bear_left_p
                energy_ok_bear = cur_h_bear < bear_left_h

                if ratio_ok_bear and price_ok_bear and energy_ok_bear:
                    df.iloc[i, df.columns.get_loc('macd_divergence')] = 'bear'
                    df.iloc[i, df.columns.get_loc('macd_l_date')] = bear_left_d
                    df.iloc[i, df.columns.get_loc('macd_l_hist')] = bear_left_h
                    df.iloc[i, df.columns.get_loc('macd_r_date')] = cur_d_bear
                    df.iloc[i, df.columns.get_loc('macd_r_hist')] = cur_h_bear

            bear_left_h = cur_h_bear
            bear_left_p = cur_p_bear
            bear_left_d = cur_d_bear
            red_count = 0

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(macd_divergence_indicator, symbol="600516", start_date="20250101", end_date="20260516")