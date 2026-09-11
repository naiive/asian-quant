#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

"""
# ============================================================
# indicator: VFI
# ============================================================
"""

def vfi_indicator(
    df,
    length: int = 130,
    coef: float = 0.15,
    vcoef: float = 2.0,
    signal_length: int = 10
) -> pd.DataFrame:
    """
                  code   open   high    low  close     volume        amount       vfi  vfi_signal  vfi_diff
    date
    2026-02-12  605008  13.44  13.45  13.11  13.12   29713.00  3.929965e+07 -3.194627   -3.567223  0.372596
    2026-02-13  605008  13.12  13.24  13.08  13.09   18347.60  2.414217e+07 -3.635874   -3.579705 -0.056169
    2026-02-24  605008  13.15  13.75  13.14  13.38   50038.40  6.713812e+07 -3.496932   -3.564655  0.067723
    2026-02-25  605008  13.38  13.52  13.37  13.42   26576.20  3.572182e+07 -3.286371   -3.514058  0.227687
    2026-02-26  605008  13.45  13.45  13.07  13.09   38915.00  5.136638e+07 -2.721259   -3.369913  0.648654
    2026-02-27  605008  13.05  13.06  12.84  12.89   35748.00  4.608218e+07 -3.192392   -3.337636  0.145244
    2026-03-02  605008  12.75  12.89  12.46  12.89   45296.60  5.736646e+07 -3.793706   -3.420558 -0.373148
    2026-03-03  605008  12.85  13.16  12.56  12.57   31793.98  4.075538e+07 -4.232672   -3.568215 -0.664457
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    typical = (df['high'] + df['low'] + df['close']) / 3
    typical_prev = typical.shift(1)

    inter = np.log(typical) - np.log(typical_prev)
    vinter = inter.rolling(window=30).std()
    cutoff = coef * vinter * df['close']

    vave = df['volume'].rolling(window=length).mean().shift(1)
    vmax = vave * vcoef
    vc = np.minimum(df['volume'], vmax)
    mf = typical - typical_prev

    vcp = np.where(mf > cutoff, vc, np.where(mf < -cutoff, -vc, 0.0))

    vfi_raw = pd.Series(vcp, index=df.index).rolling(window=length).sum() / (vave + 1e-10)

    df['vfi'] = vfi_raw.rolling(window=3).mean()
    df['vfi_signal'] = df['vfi'].ewm(span=signal_length, adjust=False).mean()
    df['vfi_diff'] = df['vfi'] - df['vfi_signal']

    return df

if __name__ == '__main__':
    from core.util.func import debug_indicator
    debug_indicator(vfi_indicator, symbol="600516", start_date="20250101", end_date="20260516")