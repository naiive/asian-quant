#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: Support Resistance Channels
# ============================================================
"""

def sr_channels_indicator(
    df,
    prd: int = 10,
    loopback: int = 290,
    channel_width_pct: int = 5
) -> pd.DataFrame:
    """
                  code  open  high   low  close      volume        amount  turnover_rate  support_high  support_low  support_pct
    date
    2026-04-14  600516  5.66  5.69  5.57   5.65   395459.96  2.227264e+08         0.9823          4.47         4.43    26.636569
    2026-04-15  600516  5.68  5.68  5.55   5.56   418583.60  2.344833e+08         1.0397          4.47         4.43    24.604966
    2026-04-16  600516  5.60  5.62  5.54   5.61   408687.27  2.280966e+08         1.0151          4.47         4.43    25.733634
    2026-04-17  600516  5.61  5.66  5.57   5.59   447373.00  2.507854e+08         1.1112          4.47         4.43    25.282167
    2026-04-20  600516  5.59  5.64  5.55   5.59   370794.36  2.075143e+08         0.9210          4.47         4.43    25.282167
    2026-04-21  600516  5.60  5.61  5.45   5.48   518689.97  2.845757e+08         1.2884          4.47         4.43    22.799097
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    n = len(df)

    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(prd, n - prd):
        h_window = highs[i - prd: i + prd + 1]
        l_window = lows[i - prd: i + prd + 1]
        if highs[i] == np.max(h_window): ph[i] = highs[i]
        if lows[i] == np.min(l_window): pl[i] = lows[i]

    h300 = df['high'].rolling(300, min_periods=1).max().values
    l300 = df['low'].rolling(300, min_periods=1).min().values
    max_cwidth = (h300 - l300) * channel_width_pct / 100

    out_hi = np.full(n, np.nan)
    out_lo = np.full(n, np.nan)

    for i in range(max(loopback, 300), n):
        curr_width = max_cwidth[i]
        curr_close = closes[i]

        start_win = i - loopback - prd
        end_win = i - prd

        win_ph = ph[start_win:end_win]
        win_pl = pl[start_win:end_win]
        p_vals = np.concatenate([win_ph[~np.isnan(win_ph)], win_pl[~np.isnan(win_pl)]])

        if len(p_vals) == 0:
            continue

        unique_p_vals = np.unique(p_vals)
        sr_candidates = []

        win_h = highs[i - loopback: i + 1]
        win_l = lows[i - loopback: i + 1]

        for p in unique_p_vals:
            in_range = p_vals[(p_vals >= p - curr_width) & (p_vals <= p + curr_width)]
            if len(in_range) == 0: continue

            hi, lo = np.max(in_range), np.min(in_range)

            if (hi - lo) <= curr_width:
                touches = np.sum(((win_h <= hi) & (win_h >= lo)) | ((win_l <= hi) & (win_l >= lo)))
                strength = len(in_range) * 20 + touches
                sr_candidates.append({'hi': hi, 'lo': lo, 'strength': strength})

        if not sr_candidates:
            continue

        sr_candidates.sort(key=lambda x: x['strength'], reverse=True)

        final_supports = []
        for cand in sr_candidates:
            if cand['hi'] < curr_close:
                is_overlap = False
                for s in final_supports:
                    if s['hi'] >= cand['hi'] >= s['lo']:
                        is_overlap = True
                        break
                if not is_overlap:
                    final_supports.append(cand)

            if len(final_supports) > 5:
                break

        if final_supports:
            lowest_s = min(final_supports, key=lambda x: x['lo'])
            out_hi[i] = lowest_s['hi']
            out_lo[i] = lowest_s['lo']

    df['support_high'] = out_hi
    df['support_low'] = out_lo
    df['support_pct'] = ((df['close'] - df['support_high']) / df['support_low']) * 100

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(sr_channels_indicator, symbol="600516", start_date="20250101", end_date="20260516")