#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: AlphaTrend
# ============================================================
"""

def atd_indicator(
    df: pd.DataFrame,
    coeff: float = 1.0,
    ap: int = 14,
    novolumedata: bool = False
) -> pd.DataFrame:
    """
                  code   open   high    low  close      volume        amount  turnover_rate  alpha_trend atd_signal
    date
    2026-01-30  002149  47.19  50.50  47.19  49.23   859362.34  4.216131e+09        17.6049    45.935000         no
    2026-02-02  002149  53.00  54.15  51.10  52.50  1415825.89  7.586378e+09        29.0045    47.641429        buy
    2026-02-03  002149  53.00  57.68  50.99  57.03  1448051.42  7.859745e+09        29.6647    47.641429         no
    2026-03-19  002149  43.60  45.86  43.00  44.00   398280.01  1.753077e+09         8.1591    49.369286         no
    2026-03-20  002149  44.11  45.30  43.00  43.23   351181.93  1.553602e+09         7.1943    48.192143       sell
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    tr = df['high'] - df['low']
    atr = tr.rolling(window=ap).mean()

    if novolumedata:
        delta = df['close'].diff()
        gain = delta.clip(lower=0).ewm(com=ap - 1, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(com=ap - 1, adjust=False).mean()
        rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
        trend_ok = rsi >= 50
    else:
        hlc3 = (df['high'] + df['low'] + df['close']) / 3
        raw_mf = hlc3 * df['volume']

        pos_mf = raw_mf.where(hlc3 > hlc3.shift(1), 0.0).rolling(ap).sum()
        neg_mf = raw_mf.where(hlc3 < hlc3.shift(1), 0.0).rolling(ap).sum()

        mfr = pos_mf / neg_mf.replace(0, np.nan)
        mfi = 100 - 100 / (1 + mfr)
        mfi = mfi.where(neg_mf != 0, 100.0)
        trend_ok = mfi >= 50

    bull_candidate = (df['low'] - atr * coeff).values
    bear_candidate = (df['high'] + atr * coeff).values
    trend_arr = trend_ok.values
    at = np.zeros(len(df))

    first_idx = atr.first_valid_index()
    if first_idx is None:
        df['alpha_trend'] = np.nan
        df['atd_signal'] = 'no'
        return df

    start = df.index.get_loc(first_idx)

    at[start] = bear_candidate[start]

    for i in range(start + 1, len(df)):
        prev = at[i - 1]
        if trend_arr[i]:
            at[i] = max(prev, bull_candidate[i])
        else:
            at[i] = min(prev, bear_candidate[i])

    at_series = pd.Series(at, index=df.index)
    at_series[:start] = np.nan

    at_lag2 = at_series.shift(2)
    at_lag1 = at_series.shift(1)

    at_lag2_lag1 = at_lag2.shift(1)

    buy_sig = (at_series > at_lag2) & (at_lag1 <= at_lag2_lag1)
    sell_sig = (at_series < at_lag2) & (at_lag1 >= at_lag2_lag1)

    signals = np.where(buy_sig, 'buy', np.where(sell_sig, 'sell', 'no'))

    df['alpha_trend'] = at_series
    df['atd_signal'] = signals

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(atd_indicator, symbol="600516", start_date="20250101", end_date="20260516")
