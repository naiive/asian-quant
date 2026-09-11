#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from collections import deque

"""
# ============================================================
# Indicator: Divergence For Many Indicators
# ============================================================
"""

def _rma(arr: np.ndarray, length: int) -> np.ndarray:
    result = np.full(len(arr), np.nan)
    if len(arr) < length:
        return result
    result[length - 1] = np.nanmean(arr[:length])
    alpha = 1.0 / length
    for i in range(length, len(arr)):
        result[i] = alpha * arr[i] + (1.0 - alpha) * result[i - 1]
    return result

def _ema(arr: np.ndarray, length: int) -> np.ndarray:
    result = np.full(len(arr), np.nan)
    first = next((i for i, x in enumerate(arr) if not np.isnan(x)), None)
    if first is None or first + length > len(arr):
        return result
    result[first + length - 1] = np.nanmean(arr[first: first + length])
    alpha = 2.0 / (length + 1)
    for i in range(first + length, len(arr)):
        result[i] = alpha * arr[i] + (1.0 - alpha) * result[i - 1]
    return result


def _sma(arr: np.ndarray, length: int) -> np.ndarray:
    return pd.Series(arr).rolling(length).mean().values

def _calc_rsi(close: np.ndarray, length: int = 14) -> np.ndarray:
    delta = np.diff(close, prepend=np.nan)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    ag = _rma(gain, length)
    al = _rma(loss, length)
    return 100.0 - 100.0 / (1.0 + ag / np.where(al == 0, np.nan, al))

def _calc_macd(close: np.ndarray, fast=12, slow=26, sig=9):
    macd_line = _ema(close, fast) - _ema(close, slow)
    histogram = macd_line - _ema(macd_line, sig)
    return macd_line, histogram

def _calc_stoch(close: np.ndarray, high: np.ndarray, low: np.ndarray, k: int = 14, d: int = 3) -> np.ndarray:
    ll = pd.Series(low).rolling(k).min().values
    hh = pd.Series(high).rolling(k).max().values
    stk = 100.0 * (close - ll) / np.where(hh - ll == 0, np.nan, hh - ll)
    return _sma(stk, d)

def _calc_cci(close: np.ndarray, length: int = 10) -> np.ndarray:
    ma = _sma(close, length)
    md = pd.Series(close).rolling(length).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True).values
    return (close - ma) / (0.015 * np.where(md == 0, np.nan, md))

def _calc_mom(close: np.ndarray, length: int = 10) -> np.ndarray:
    return close - np.concatenate([np.full(length, np.nan), close[:-length]])

def _calc_obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    direction = pd.Series(np.sign(np.diff(close, prepend=np.nan))).fillna(0).values
    return np.cumsum(direction * volume)

def _calc_vwmacd(close: np.ndarray, volume: np.ndarray, fast: int = 12, slow: int = 26) -> np.ndarray:
    cv = close * volume
    vf = pd.Series(cv).rolling(fast).sum().values / pd.Series(volume).rolling(fast).sum().values
    vs = pd.Series(cv).rolling(slow).sum().values / pd.Series(volume).rolling(slow).sum().values
    return vf - vs

def _calc_cmf(close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray, length: int = 21) -> np.ndarray:
    hl = np.where(high - low == 0, np.nan, high - low)
    mfv = ((close - low) - (high - close)) / hl * volume
    return (pd.Series(mfv).rolling(length).sum().values /
            pd.Series(volume).rolling(length).sum().values)

def _calc_mfi(close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray, length: int = 14) -> np.ndarray:
    tp = (high + low + close) / 3.0
    mf = tp * volume
    prev = np.concatenate([np.full(1, np.nan), tp[:-1]])
    pos = pd.Series(np.where(tp > prev, mf, 0.0)).rolling(length).sum().values
    neg = pd.Series(np.where(tp < prev, mf, 0.0)).rolling(length).sum().values
    return 100.0 - 100.0 / (1.0 + pos / np.where(neg == 0, np.nan, neg))

def _build_pivot_triggers(price: np.ndarray, period: int):
    n = len(price)
    pl_trig: dict = {}
    ph_trig: dict = {}
    for body in range(period, n - period):
        window = price[body - period: body + period + 1]
        pv = price[body]
        trigger = body + period
        if pv == np.min(window):
            pl_trig[trigger] = pv
        if pv == np.max(window):
            ph_trig[trigger] = pv
    return pl_trig, ph_trig

def _check_pos_reg(src: np.ndarray, close: np.ndarray, i: int, pl_buf: list, max_pp: int, max_bars: int, prd: int, dont_confirm: bool = False) -> bool:
    sp = 0 if dont_confirm else 1

    if i - sp < 0:
        return False

    if not dont_confirm:
        if np.isnan(src[i]) or np.isnan(src[i - 1]):
            return False
        if not (src[i] > src[i - 1] or close[i] > close[i - 1]):
            return False

    s_sp = src[i - sp]
    c_sp = close[i - sp]
    if np.isnan(s_sp) or np.isnan(c_sp):
        return False

    for x, (trig, pv) in enumerate(pl_buf):
        if x >= max_pp:
            break
        length = i - trig + prd
        if length > max_bars:
            break
        if length <= 5:
            continue
        if length <= sp:
            continue

        src_body = src[i - length]
        if np.isnan(src_body):
            continue

        if not (s_sp > src_body and c_sp < pv):
            continue

        slope1 = (s_sp - src_body) / (length - sp)
        slope2 = (c_sp - close[i - length]) / (length - sp)
        vl1 = s_sp - slope1
        vl2 = c_sp - slope2
        valid = True
        for y in range(1 + sp, length):
            idx = i - y
            if src[idx] < vl1 or close[idx] < vl2:
                valid = False
                break
            vl1 -= slope1
            vl2 -= slope2

        if valid:
            return True

    return False

def _check_neg_reg(src: np.ndarray, close: np.ndarray, i: int, ph_buf: list, max_pp: int, max_bars: int, prd: int, dont_confirm: bool = False) -> bool:
    sp = 0 if dont_confirm else 1

    if i - sp < 0:
        return False

    if not dont_confirm:
        if np.isnan(src[i]) or np.isnan(src[i - 1]):
            return False
        if not (src[i] < src[i - 1] or close[i] < close[i - 1]):
            return False

    s_sp = src[i - sp]
    c_sp = close[i - sp]
    if np.isnan(s_sp) or np.isnan(c_sp):
        return False

    for x, (trig, pv) in enumerate(ph_buf):
        if x >= max_pp:
            break
        length = i - trig + prd
        if length > max_bars:
            break
        if length <= 5:
            continue
        if length <= sp:
            continue

        src_body = src[i - length]
        if np.isnan(src_body):
            continue

        if not (s_sp < src_body and c_sp > pv):
            continue

        slope1 = (s_sp - src_body) / (length - sp)
        slope2 = (c_sp - close[i - length]) / (length - sp)
        vl1 = s_sp - slope1
        vl2 = c_sp - slope2
        valid = True
        for y in range(1 + sp, length):
            idx = i - y
            if src[idx] > vl1 or close[idx] > vl2:
                valid = False
                break
            vl1 -= slope1
            vl2 -= slope2

        if valid:
            return True

    return False


def div_indicator(
    df: pd.DataFrame,
    prd: int = 5,
    source: str = "Close",
    max_pp: int = 10,
    max_bars: int = 100,
    dont_confirm: bool = True,
    calc_macd: bool = True,
    calc_macd_hist: bool = True,
    calc_rsi: bool = True,
    calc_stoch: bool = True,
    calc_cci: bool = True,
    calc_mom: bool = True,
    calc_obv: bool = True,
    calc_vwmacd: bool = True,
    calc_cmf: bool = True,
    calc_mfi: bool = True,
) -> pd.DataFrame:
    """
                  code  open  high   low  close      volume        amount  turnover_rate  macd_pos_div  macd_neg_div  hist_pos_div  hist_neg_div  rsi_pos_div  rsi_neg_div  stoch_pos_div  stoch_neg_div  cci_pos_div  cci_neg_div  mom_pos_div  mom_neg_div  obv_pos_div  obv_neg_div  vwmacd_pos_div  vwmacd_neg_div  cmf_pos_div  cmf_neg_div  mfi_pos_div  mfi_neg_div  pos_div_count  neg_div_count                    pos_div_detail           neg_div_detail
    date
    2026-02-02  600516  5.65  5.74  5.41   5.44   915425.53  5.107370e+08         2.2738         False         False         False         False        False        False          False          False        False        False        False        False        False        False           False           False        False        False        False        False              0              0
    2026-02-03  600516  5.54  5.69  5.51   5.68   714229.68  4.007664e+08         1.7741          True         False          True         False        False        False          False          False         True        False        False        False        False        False            True           False         True        False         True        False              6              0      macd|hist|cci|vwmacd|cmf|mfi
    2026-02-04  600516  5.67  5.90  5.60   5.87   930281.18  5.357082e+08         2.3107         False         False         False         False        False        False          False          False        False        False        False        False        False        False           False           False        False        False        False        False              0              0
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if "date" not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

    close = df["close"].values.astype(float)
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    volume = df["volume"].values.astype(float)
    n = len(df)

    macd_line, hist_arr = _calc_macd(close)
    rsi_arr = _calc_rsi(close)
    stoch_arr = _calc_stoch(close, high, low)
    cci_arr = _calc_cci(close)
    mom_arr = _calc_mom(close)
    obv_arr = _calc_obv(close, volume)
    vwmacd_arr = _calc_vwmacd(close, volume)
    cmf_arr = _calc_cmf(close, high, low, volume)
    mfi_arr = _calc_mfi(close, high, low, volume)

    if source == "Close":
        pl_trig, ph_trig = _build_pivot_triggers(close, prd)
    else:
        _, ph_trig = _build_pivot_triggers(high, prd)
        pl_trig, _ = _build_pivot_triggers(low, prd)

    indicators = [
        ("macd", calc_macd, macd_line),
        ("hist", calc_macd_hist, hist_arr),
        ("rsi", calc_rsi, rsi_arr),
        ("stoch", calc_stoch, stoch_arr),
        ("cci", calc_cci, cci_arr),
        ("mom", calc_mom, mom_arr),
        ("obv", calc_obv, obv_arr),
        ("vwmacd", calc_vwmacd, vwmacd_arr),
        ("cmf", calc_cmf, cmf_arr),
        ("mfi", calc_mfi, mfi_arr),
    ]

    results: dict = {}
    for name, _, _ in indicators:
        results[f"{name}_pos_div"] = np.zeros(n, dtype=bool)
        results[f"{name}_neg_div"] = np.zeros(n, dtype=bool)

    pl_buf: deque = deque(maxlen=20)
    ph_buf: deque = deque(maxlen=20)

    for i in range(n):

        if i in pl_trig:
            pl_buf.appendleft((i, pl_trig[i]))
        if i in ph_trig:
            ph_buf.appendleft((i, ph_trig[i]))

        if i < prd * 2 + 5:
            continue

        pl_list = list(pl_buf)
        ph_list = list(ph_buf)

        for name, enabled, src_arr in indicators:
            if not enabled:
                continue

            if pl_list:
                if _check_pos_reg(src_arr, close, i, pl_list, max_pp, max_bars, prd, dont_confirm):
                    results[f"{name}_pos_div"][i] = True

            if ph_list:
                if _check_neg_reg(src_arr, close, i, ph_list, max_pp, max_bars, prd, dont_confirm):
                    results[f"{name}_neg_div"][i] = True

    for col, arr in results.items():
        df[col] = arr

    pos_cols = [c for c in results if c.endswith("_pos_div")]
    neg_cols = [c for c in results if c.endswith("_neg_div")]
    df["pos_div_count"] = sum(df[c].astype(int) for c in pos_cols)
    df["neg_div_count"] = sum(df[c].astype(int) for c in neg_cols)

    indicator_names = [name for name, _, _ in indicators]
    df["pos_div_detail"] = [
        "|".join(name for name in indicator_names if results[f"{name}_pos_div"][i])
        for i in range(n)
    ]
    df["neg_div_detail"] = [
        "|".join(name for name in indicator_names if results[f"{name}_neg_div"][i])
        for i in range(n)
    ]

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(div_indicator, symbol="600516", start_date="20250101", end_date="20260516")