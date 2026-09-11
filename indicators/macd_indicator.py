#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: MACD
# ============================================================
"""

def macd_indicator(
    df: pd.DataFrame,
    fast_length: int = 12,
    slow_length: int = 26,
    signal_length: int = 9
) -> pd.DataFrame:
    """
                  code   open   high    low  close      volume        amount  turnover_rate      macd    signal  macd_hist hist_color cross_signal cross_trend  cross_streak  macd_zscore
    date
    2026-03-17  002460  70.60  71.33  68.40  68.49   308917.43  2.149445e+09         2.5501  0.337723  0.193539   0.144184      green           no        bull             3     0.246240
    2026-03-18  002460  68.49  68.77  65.54  66.65   379439.35  2.529373e+09         3.1323  0.117868  0.178763  -0.060894        red         sell        bear             1    -0.003988
    2026-03-19  002460  65.45  66.40  63.13  63.44   442127.38  2.849958e+09         3.6498 -0.311794  0.143433  -0.455227        red           no        bear             2    -0.500083
    2026-03-20  002460  64.50  69.78  63.26  67.43   879258.19  5.905522e+09         7.2583 -0.326580  0.111193  -0.437773     maroon           no        bear             3    -0.466210
    2026-03-23  002460  66.40  69.99  66.33  67.58   717228.70  4.894235e+09         5.9208 -0.322477  0.071904  -0.394381     maroon           no        bear             4    -0.399776
    2026-03-24  002460  68.92  69.55  65.58  69.21   602362.42  4.093112e+09         4.9725 -0.185559  0.031793  -0.217352     maroon           no        bear             5    -0.160942
    2026-03-25  002460  70.55  71.38  68.61  70.63   633043.31  4.436075e+09         5.2258  0.037104  0.010020   0.027083       lime          buy        bull             1     0.161950
    2026-03-26  002460  70.37  73.77  70.01  72.43   766407.07  5.548376e+09         6.3267  0.354722  0.014121   0.340601       lime           no        bull             2     0.574030
    2026-03-27  002460  71.49  79.67  71.49  79.67  1312133.02  1.007418e+10        10.8317  1.177075  0.097565   1.079511       lime           no        bull             3     1.524604
    2026-03-30  002460  81.00  81.50  78.00  80.15  1175708.76  9.389592e+09         9.7055  1.846246  0.265178   1.581068       lime           no        bull             4     2.129464
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    fast_ma = df["close"].ewm(span=fast_length, adjust=False).mean()
    slow_ma = df["close"].ewm(span=slow_length, adjust=False).mean()

    df["macd"] = fast_ma - slow_ma
    df["signal"] = df["macd"].rolling(window=signal_length).mean()
    df["macd_hist"] = df["macd"] - df["signal"]

    df["macd_hist_prev"] = df["macd_hist"].shift(1)

    conditions = [
        (df["macd_hist"] > 0) & (df["macd_hist"] > df["macd_hist_prev"]),
        (df["macd_hist"] > 0) & (df["macd_hist"] <= df["macd_hist_prev"]),
        (df["macd_hist"] <= 0) & (df["macd_hist"] < df["macd_hist_prev"]),
        (df["macd_hist"] <= 0) & (df["macd_hist"] >= df["macd_hist_prev"])
    ]
    choices = ["lime", "green", "red", "maroon"]
    df["hist_color"] = np.select(conditions, choices, default="blue")

    df["cm_prev_macd"] = df["macd"].shift(1)
    df["cm_prev_signal"] = df["signal"].shift(1)

    df["cross_signal"] = 'no'
    df.loc[(df["cm_prev_macd"] < df["cm_prev_signal"]) & (df["macd"] >= df["signal"]), "cross_signal"] = 'buy'
    df.loc[(df["cm_prev_macd"] > df["cm_prev_signal"]) & (df["macd"] <= df["signal"]), "cross_signal"] = 'sell'

    status_map = {'buy': 'bull', 'sell': 'bear'}
    df["cross_trend"] = df["cross_signal"].map(status_map)
    df["cross_trend"] = df["cross_trend"].ffill()

    initial_status = pd.Series(
        np.where(df["macd"] >= df["signal"], 'bull', 'bear'),
        index=df.index
    )
    df["cross_trend"] = df["cross_trend"].fillna(initial_status)

    status_changed = df["cross_trend"] != df["cross_trend"].shift(1)
    df["cross_streak"] = status_changed.cumsum()
    df["cross_streak"] = df.groupby("cross_streak").cumcount() + 1

    roll_window = 120
    hist_mean = df["macd_hist"].rolling(roll_window).mean()
    hist_std = df["macd_hist"].rolling(roll_window).std()
    df["macd_zscore"] = (df["macd_hist"] - hist_mean) / hist_std

    df.drop(columns=["macd_hist_prev", "cm_prev_macd", "cm_prev_signal"], inplace=True)

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(macd_indicator, symbol="600516", start_date="20250101", end_date="20260516")