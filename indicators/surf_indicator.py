#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
============================================================
Indicator: Surf Indicator
============================================================
"""

def surf_indicator(
    df: pd.DataFrame,
    timeframe: str = "d",
    rsi_length: int = 14,
    # 底部（Accumulation）阈值
    daily_rsi_threshold: int = 30,
    weekly_rsi_threshold: int = 35,
    monthly_rsi_threshold: int = 45,
    # 顶部（Distribution）阈值
    daily_top_threshold: int = 70,
    weekly_top_threshold: int = 65,
    monthly_top_threshold: int = 55,
    # SMA 长度
    daily_sma_len: int = 200,
    weekly_sma_len: int = 200,
    monthly_sma_len: int = 46
) -> pd.DataFrame:
    """
                  code        open        high         low       close     volume        amount  turnover_rate  zone
    date
    2026-01-16  301080   60.400000   61.630000   59.670000   61.490000   17112.20  1.038519e+08         1.3581  distribution
    2026-01-19  301080   61.490000   62.430000   60.590000   60.720000   19586.10  1.197856e+08         1.5545  no
    2026-01-20  301080   60.840000   62.180000   60.600000   60.960000   16872.01  1.033517e+08         1.3391  no
    2026-01-21  301080   60.500000   63.330000   60.460000   62.650000   17274.13  1.076322e+08         1.3710  distribution
    2026-01-22  301080   62.750000   63.880000   61.800000   62.620000   15882.30  1.001162e+08         1.2605  distribution
    2026-02-27  301080   48.350000   48.910000   47.800000   48.140000   38361.86  1.846632e+08         3.0446  no
    2026-03-02  301080   47.280000   47.680000   44.930000   45.120000   66129.72  3.030135e+08         5.2485  accum
    2026-03-03  301080   45.200000   45.870000   43.800000   43.910000   42964.59  1.920627e+08         3.4099  accum
    2026-03-04  301080   43.620000   44.300000   43.380000   43.540000   26492.71  1.158480e+08         2.1026  accum

    """

    tf = timeframe.upper()
    if tf not in ("D", "W", "M"):
        raise ValueError("timeframe 仅支持 'D' (日线), 'W' (周线), 'M' (月线)")

    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
        else:
            raise ValueError("DataFrame 必须包含 DatetimeIndex 或 'date' 列")

    df.sort_index(inplace=True)

    params = {
        "D": (daily_sma_len, daily_rsi_threshold, daily_top_threshold),
        "W": (weekly_sma_len, weekly_rsi_threshold, weekly_top_threshold),
        "M": (monthly_sma_len, monthly_rsi_threshold, monthly_top_threshold),
    }
    sma_len, thresh_bottom, thresh_top = params[tf]

    close_s = df["close"].astype(float)
    low_s = df["low"].astype(float)
    high_s = df["high"].astype(float)

    sma_s = close_s.rolling(window=sma_len, min_periods=sma_len).mean()

    delta = close_s.diff()
    up = delta.clip(lower=0).ewm(alpha=1.0 / rsi_length, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1.0 / rsi_length, adjust=False).mean()
    rsi_s = 100.0 - (100.0 / (1.0 + up / down))
    rsi_s.iloc[:rsi_length] = np.nan

    in_accum_zone = (low_s <= sma_s) & (rsi_s < thresh_bottom)
    in_distribution_zone = (high_s >= sma_s) & (rsi_s > thresh_top)

    zone_s = pd.Series('no', index=df.index, dtype=object)
    zone_s[in_distribution_zone] = "distribution"
    zone_s[in_accum_zone] = "accum"

    df["zone"] = zone_s

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator

    debug_indicator(surf_indicator, symbol="600276", start_date="20200101", end_date="20260816")
