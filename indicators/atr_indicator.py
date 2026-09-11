#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: Average True Range Stop Loss Finder
# ============================================================
"""

def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs()
        ],
        axis=1,
    ).max(axis=1)

    return tr

def ma_smoothing(series: pd.Series, length: int, method: str) -> pd.Series:
    method = method.upper()

    if method == "SMA":
        return series.rolling(length).mean()

    if method == "EMA":
        return series.ewm(span=length, adjust=False).mean()

    if method == "RMA":
        rma = np.full(len(series), np.nan)

        if len(series) < length:
            return pd.Series(rma, index=series.index)

        rma[length - 1] = series.iloc[:length].mean()

        alpha = 1 / length
        for i in range(length, len(series)):
            rma[i] = alpha * series.iloc[i] + (1 - alpha) * rma[i - 1]

        return pd.Series(rma, index=series.index)

    if method == "WMA":
        weights = np.arange(1, length + 1)

        return series.rolling(length).apply(
            lambda x: np.dot(x, weights) / weights.sum(),
            raw=True,
        )

    raise ValueError(f"Unknown smoothing method: {method}")

def atr_indicator(
    df: pd.DataFrame,
    atr_length: int = 14,
    atr_mult: float = 1,
    atr_smooth: str = "RMA"
) -> pd.DataFrame:
    """
    code        date  open  high   low  close       volume        amount       atr  atr_mult  atr_short_stop  atr_long_stop
    600628  2025-12-08  7.77  7.83  7.71   7.77   13255088.0  1.028871e+08  0.209239  0.313858        8.143858       7.396142
    600628  2025-12-09  7.75  7.95  7.67   7.86   25256601.0  1.982662e+08  0.214293  0.321440        8.271440       7.348560
    600628  2025-12-10  7.93  8.10  7.85   7.90   26390258.0  2.096010e+08  0.216844  0.325265        8.425265       7.524735
    600628  2025-12-11  7.85  7.92  7.56   7.64   23619600.0  1.814402e+08  0.227069  0.340604        8.260604       7.219396
    600628  2025-12-12  7.65  7.65  7.39   7.40   20526300.0  1.531835e+08  0.229421  0.344132        7.994132       7.045868
    600628  2025-12-15  7.43  8.14  7.41   7.95   52808074.0  4.177851e+08  0.265891  0.398837        8.538837       7.011163
    600628  2025-12-16  8.00  8.47  8.00   8.10   68590070.0  5.611935e+08  0.284042  0.426063        8.896063       7.573937
    600628  2025-12-17  8.22  8.31  7.99   8.08   47891061.0  3.907951e+08  0.286610  0.429915        8.739915       7.560085
    600628  2025-12-18  8.00  8.89  7.99   8.89   86095168.0  7.394343e+08  0.330424  0.495636        9.385636       7.494364
    600628  2025-12-19  9.00  9.77  8.88   9.11  121830916.0  1.129386e+09  0.370394  0.555590       10.325590       8.324410
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    tr = true_range(df)

    atr = ma_smoothing(tr, atr_length, atr_smooth)

    df["atr"] = atr
    df["atr_mult"] = atr * atr_mult

    df["atr_short_stop"] = df["high"] + df["atr_mult"]

    df["atr_long_stop"] = df["low"] - df["atr_mult"]

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(atr_indicator, symbol="600516", start_date="20250101", end_date="20260516")