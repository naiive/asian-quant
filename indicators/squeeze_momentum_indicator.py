#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from enum import Enum

"""
# ============================================================
# Indicator: Squeeze Momentum
# ============================================================
"""

class MomentumHistogramColor(Enum):
    BULL_ACCELERATING = "lime"
    BULL_DECELERATING = "green"
    BEAR_ACCELERATING = "red"
    BEAR_DECELERATING = "maroon"
    NEUTRAL = "neutral"
    UNDEFINED = "undefined"

def tv_linreg(y: pd.Series, length: int) -> float:
    if pd.isna(y).any() or len(y) < length:
        return np.nan
    x = np.arange(length)
    y_vals = y.values[-length:]
    a = np.vstack([x, np.ones(length)]).T
    try:
        m, b = np.linalg.lstsq(a, y_vals, rcond=None)[0]
        return m * (length - 1) + b
    except (np.linalg.LinAlgError, ValueError):
        return np.nan

def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def get_squeeze_momentum_histogram_color(val, val_prev):
    if pd.isna(val) or pd.isna(val_prev):
        return MomentumHistogramColor.UNDEFINED.value

    if val > 0:
        return (
            MomentumHistogramColor.BULL_ACCELERATING.value
            if val > val_prev
            else MomentumHistogramColor.BULL_DECELERATING.value
        )
    elif val < 0:
        return (
            MomentumHistogramColor.BEAR_ACCELERATING.value
            if val < val_prev
            else MomentumHistogramColor.BEAR_DECELERATING.value
        )
    else:
        return MomentumHistogramColor.NEUTRAL.value

def add_squeeze_counter(df: pd.DataFrame)-> pd.DataFrame:
    counter = 0
    current_state = None
    sqz_id_list = []
    for status in df["sqz_status"]:
        if status in ["on", "off"]:
            if status == current_state:
                counter += 1
            else:
                current_state = status
                counter = 1
            sqz_id_list.append(counter)
        else:
            current_state = None
            counter = 0
            sqz_id_list.append(0)
    df["sqz_id"] = sqz_id_list
    return df

def add_color_counter(df: pd.DataFrame) -> pd.DataFrame:
    counter = 0
    current_color = None
    sqz_hcolor_id_list = []
    skip_colors = {MomentumHistogramColor.UNDEFINED.value, MomentumHistogramColor.NEUTRAL.value}

    for color in df["sqz_hcolor"]:
        if color in skip_colors:
            current_color = None
            counter = 0
            sqz_hcolor_id_list.append(0)
        else:
            if color == current_color:
                counter += 1
            else:
                current_color = color
                counter = 1
            sqz_hcolor_id_list.append(counter)

    df["sqz_hcolor_id"] = sqz_hcolor_id_list
    return df

def squeeze_momentum_indicator(
    df: pd.DataFrame,
    length: int = 20,
    mult: float = 1.8,
    length_kc: int = 20,
    mult_kc: float = 1.5,
    use_true_range: bool = True
)-> pd.DataFrame:
    """
                  code  open  high   low  close      volume        amount sqz_status  sqz_hvalue   sqz_hstrength  sqz_id sqz_hcolor  sqz_hcolor_id
    date
    2026-02-04  600516  5.67  5.90  5.60   5.87   930281.18  5.357082e+08         off   -0.108489           50.0      25     maroon              1
    2026-02-05  600516  5.81  5.81  5.61   5.66   765729.15  4.345003e+08         on   -0.138382            60.0      26        red              1
    2026-02-06  600516  5.60  5.77  5.55   5.68   540519.22  3.083211e+08         off   -0.147196           65.0      27        red              2
    2026-02-09  600516  5.75  5.81  5.72   5.76   413103.87  2.381069e+08         off   -0.127025           55.0      28     maroon              1
    2026-02-10  600516  5.78  5.81  5.68   5.70   399433.20  2.279536e+08         on   -0.127429            60.0      29       lime              1
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    close, high, low = df['close'], df['high'], df['low']

    basis = close.rolling(length).mean()
    dev = mult * close.rolling(length).std(ddof=0)
    upper_bb, lower_bb = basis + dev, basis - dev

    ma = close.rolling(length_kc).mean()
    r = true_range(df) if use_true_range else (high - low)
    rangema = r.rolling(length_kc).mean()
    upper_kc, lower_kc = ma + rangema * mult_kc, ma - rangema * mult_kc

    sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)
    df["sqz_status"] = np.select([sqz_on, sqz_off], ["on", "off"], default="no")

    highest_h = high.rolling(length_kc).max()
    lowest_l = low.rolling(length_kc).min()
    avg_hl = (highest_h + lowest_l) / 2
    sma_close = close.rolling(length_kc).mean()
    mid = (avg_hl + sma_close) / 2
    source_mid = close - mid
    histogram_value = source_mid.rolling(length_kc).apply(lambda x: tv_linreg(pd.Series(x), length_kc), raw=False)

    df["sqz_hvalue"] = histogram_value
    abs_h = df["sqz_hvalue"].abs()
    df["sqz_hstrength"] = abs_h.rolling(length_kc).apply(
        lambda x: (x.rank(pct=True).iloc[-1] * 100) if not x.isna().all() else np.nan
    )

    df["sqz_pre_hvalue"] = histogram_value.shift(1)

    df = add_squeeze_counter(df)

    df["sqz_hcolor"] = df.apply(lambda re: get_squeeze_momentum_histogram_color(re["sqz_hvalue"], re["sqz_pre_hvalue"]), axis=1)

    df.drop(columns=["sqz_pre_hvalue"], inplace=True)

    df = add_color_counter(df)

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(squeeze_momentum_indicator, symbol="600516", start_date="20250101", end_date="20260516")