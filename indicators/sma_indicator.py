#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# Indicator: SMA
# ============================================================
"""

def sma_indicator(
    df: pd.DataFrame,
    n: int = 20,
    cc: int = 1
) -> pd.DataFrame:
    """
                  code   open   high    low  close       volume          amount  turnover_rate    sma sma_color sma_node
    date
    2026-09-03  600516 5.2200 5.2700 5.1800 5.2100  357167.8500  186165318.1800         0.8872 5.1785       red       no
    2026-09-04  600516 5.2200 5.2700 5.1800 5.2100  355590.8800  185834932.1700         0.8832 5.1795     green     bull
    2026-09-07  600516 5.1900 5.2100 5.1600 5.1800  280027.4900  145142926.5600         0.6956 5.1775       red     bear
    2026-09-08  600516 5.1700 5.3100 5.1600 5.2600  451211.7000  236424689.1400         1.1208 5.1825     green     bull
    2026-09-09  600516 5.2500 5.3000 5.2200 5.2900  417263.0300  219720978.3200         1.0364 5.1865     green       no
    2026-09-10  600516 5.2600 5.3100 5.2100 5.2700  353653.7100  186039493.2600         0.8784 5.1825       red     bear
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    ma = df['close'].rolling(window=n, min_periods=n).mean()
    prev_ma = ma.shift(1)
    valid = ma.notna()

    up = (ma >= prev_ma) | prev_ma.isna()
    prev_up = up.shift(1, fill_value=True)

    turn_dn = (~up) & prev_up
    turn_up = up & (~prev_up)

    if cc == 1:
        color = np.where(up, 'green', 'red')
        node = np.select([turn_up, turn_dn], ['bull', 'bear'], default='no')
    else:
        color = np.full(len(df), 'cyan', dtype=object)
        node = np.full(len(df), 'no', dtype=object)

    color = pd.Series(color, index=df.index, dtype=object).where(valid, None)
    node = pd.Series(node, index=df.index, dtype=object).where(valid, 'no')

    df['sma'] = ma.round(4)
    df['sma_color'] = color
    df['sma_node'] = node

    pd.options.display.float_format = '{:.4f}'.format

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(sma_indicator, symbol="600516", start_date="20250101", end_date="20261116")