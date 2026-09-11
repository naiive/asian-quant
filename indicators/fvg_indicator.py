#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: Fair Value Gap
# ============================================================
"""

def fvg_indicator(
    df: pd.DataFrame,
    threshold_pct: float = 0.0,
    auto_threshold: bool = False,
) -> pd.DataFrame:
    """
                  code   open   high    low  close     volume        amount fvg_type  fvg_high  fvg_low  fvg_gap_pct  fvg_mitigated
    date
    2025-01-07  600750  21.26  21.44  20.86  21.40   86608.00  1.934354e+08     bear     21.53    21.44     0.004198          False
    2025-01-08  600750  21.44  21.59  20.86  21.35   75945.00  1.706807e+08       no       NaN      NaN          NaN          False
    2025-01-09  600750  21.15  21.44  20.79  20.82   70308.00  1.564808e+08       no       NaN      NaN          NaN          False
    2025-01-10  600750  20.72  20.89  20.46  20.46   53571.00  1.167562e+08       no       NaN      NaN          NaN          False
    2025-01-13  600750  20.40  20.61  20.22  20.35   47884.00  1.033883e+08     bear     20.79    20.61     0.008734          False
    2025-01-14  600750  20.43  20.91  20.24  20.86   73626.00  1.610289e+08       no       NaN      NaN          NaN           True
    2025-01-15  600750  20.85  21.18  20.65  20.92   58953.00  1.307279e+08     bull     20.65    20.61     0.001941          False
    2025-01-16  600750  20.92  21.19  20.71  20.84   42209.00  9.339890e+07       no       NaN      NaN          NaN          False
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    if auto_threshold:
        threshold_series = ((df["high"] - df["low"]) / df["low"]).cumsum() / (
            np.arange(len(df)) + 1
        )
    else:
        threshold_series = threshold_pct / 100.0

    df["fvg_type"] = 'no'
    df["fvg_high"] = np.nan
    df["fvg_low"] = np.nan
    df["fvg_gap_pct"] = np.nan
    df["fvg_mitigated"] = False

    for i in range(2, len(df)):
        high_2 = df["high"].iloc[i - 2]
        low_2 = df["low"].iloc[i - 2]
        close_1 = df["close"].iloc[i - 1]

        high = df["high"].iloc[i]
        low = df["low"].iloc[i]

        threshold = threshold_series.iloc[i] if auto_threshold else threshold_series

        bull_gap_pct = (low - high_2) / high_2 if high_2 != 0 else 0
        bull_fvg = (
            low > high_2
            and close_1 > high_2
            and bull_gap_pct > threshold
        )

        bear_gap_pct = (low_2 - high) / high if high != 0 else 0
        bear_fvg = (
            high < low_2
            and close_1 < low_2
            and bear_gap_pct > threshold
        )

        if bull_fvg:
            df.at[df.index[i], "fvg_type"] = "bull"
            df.at[df.index[i], "fvg_high"] = low
            df.at[df.index[i], "fvg_low"] = high_2
            df.at[df.index[i], "fvg_gap_pct"] = bull_gap_pct

        elif bear_fvg:
            df.at[df.index[i], "fvg_type"] = "bear"
            df.at[df.index[i], "fvg_high"] = low_2
            df.at[df.index[i], "fvg_low"] = high
            df.at[df.index[i], "fvg_gap_pct"] = bear_gap_pct

    active_fvgs = []

    for i in range(len(df)):
        row = df.iloc[i]
        if row["fvg_type"] in ("bull", "bear"):
            active_fvgs.append(
                {
                    "type": row["fvg_type"],
                    "high": row["fvg_high"],
                    "low": row["fvg_low"],
                }
            )
        close = row["close"]
        for fvg in active_fvgs[:]:
            if fvg["type"] == "bull" and close < fvg["low"]:
                df.at[df.index[i], "fvg_mitigated"] = True
                active_fvgs.remove(fvg)

            elif fvg["type"] == "bear" and close > fvg["high"]:
                df.at[df.index[i], "fvg_mitigated"] = True
                active_fvgs.remove(fvg)

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(fvg_indicator, symbol="600516", start_date="20250101", end_date="20260516")