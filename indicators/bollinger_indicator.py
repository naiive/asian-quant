#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

"""
# ============================================================
# Indicator: Bollinger Bands
# ============================================================
"""

def bollinger_indicator(
    df: pd.DataFrame,
    bb_length: int = 20,
    bb_mult: float = 1.2
) -> pd.DataFrame:
    """
                  code   open   high    low  close     volume        amount   bb_basis    bb_std   bb_upper  bb_lower     bb_bw  bb_bw_rank
    date
    2025-12-30  600628   8.29   8.29   7.95   7.99   344781.0  2.779549e+08   8.438333  0.376052   9.115227  7.761440  0.160433        11.8
    2025-12-31  600628   8.07   8.09   7.82   7.86   220780.0  1.744169e+08   8.430833  0.387403   9.128159  7.733508  0.165423        10.9
    2026-01-05  600628   7.88   7.93   7.81   7.93   209938.0  1.652139e+08   8.416667  0.403380   9.142750  7.690583  0.172535        10.2
    2026-01-06  600628   7.89   8.05   7.86   8.03   279938.0  2.232038e+08   8.412500  0.407411   9.145841  7.679159  0.174345         9.9
    2026-01-07  600628   7.99   8.59   7.93   8.45   546376.0  4.546370e+08   8.375833  0.379365   9.058689  7.692977  0.163054        11.3
    2026-01-08  600628   8.20   8.43   8.11   8.32   406303.0  3.352427e+08   8.310000  0.300787   8.851416  7.768584  0.130305        18.0
    2026-01-09  600628   8.27   8.53   8.27   8.48   368394.0  3.107006e+08   8.283333  0.265513   8.761256  7.805411  0.115394        22.5
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    df['bb_basis'] = df['close'].rolling(window=bb_length).mean()

    df['bb_std'] = df['close'].rolling(window=bb_length).std()

    df['bb_upper'] = df['bb_basis'] + (bb_mult * df['bb_std'])

    df['bb_lower'] = df['bb_basis'] - (bb_mult * df['bb_std'])

    df['bb_bw'] = (df['bb_upper'] - df['bb_lower']) / df['bb_basis']

    df['bb_bw_rank'] = df['bb_bw'].rank(pct=True, ascending=False) * 100

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(bollinger_indicator, symbol="600516", start_date="20250101", end_date="20260516")