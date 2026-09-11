#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

"""
# ============================================================
# Indicator: Volume Spike
# ============================================================
"""

def volume_spike_indicator(
    df: pd.DataFrame,
    vol_length: int = 5,
    vol_ratio_threshold: float = 1.5
) -> pd.DataFrame:
    """
                  code   open   high    low  close       volume        amount      vol_ma  vol_ratio  prev_close  is_up  is_volume_expand  is_volume_up
    date
    2024-01-10  600628   7.20   7.87   7.08   7.87   21095542.0  1.613236e+08   7633781.2   2.763446        7.15   True              True          True
    2024-01-11  600628   8.07   8.37   7.56   7.67   50971297.0  4.014422e+08  17105444.2   2.979829        7.87  False              True         False
    2024-01-12  600628   7.62   7.65   7.40   7.42   32528748.0  2.468451e+08  22881017.4   1.421648        7.67  False             False         False
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    df["vol_ma"] = df["volume"].rolling(vol_length).mean()

    df["vol_ratio"] = df["volume"] / df["vol_ma"]

    df["prev_close"] = df["close"].shift(1)

    df["is_up"] = df["close"] > df["prev_close"]

    df["is_volume_expand"] = df["vol_ratio"] >= vol_ratio_threshold

    df["is_volume_up"] = df["is_up"] & df["is_volume_expand"]

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(volume_spike_indicator, symbol="600516", start_date="20250101", end_date="20260516")