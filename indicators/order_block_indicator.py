#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

"""
# ============================================================
# Indicator: Order Block
# ============================================================
"""

BULLISH, BEARISH, ATR_METHOD, CLOSE_MITIGATION, HIGHLOW_MITIGATION = 1, -1, "atr", "close", "highlow"

def compute_volatility(df: pd.DataFrame, method: str = ATR_METHOD, atr_period: int = 200) -> pd.Series:
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    if method == ATR_METHOD:
        return tr.rolling(atr_period, min_periods=1).mean()
    return tr.expanding().mean()

def compute_parsed_high_low(df: pd.DataFrame, volatility: pd.Series):
    high_vol = (df["high"] - df["low"]) >= 2 * volatility
    parsed_high = np.where(high_vol, df["low"], df["high"])
    parsed_low = np.where(high_vol, df["high"], df["low"])
    return (pd.Series(parsed_high, index=df.index),
            pd.Series(parsed_low, index=df.index))

def compute_legs(high: np.ndarray, low: np.ndarray, size: int) -> np.ndarray:
    n = len(high)
    leg = np.zeros(n, dtype=int)
    for i in range(size, n):
        pivot_high = high[i - size]
        pivot_low = low[i - size]
        win_high = high[i - size + 1: i + 1].max()
        win_low = low[i - size + 1: i + 1].min()
        if pivot_high > win_high:
            leg[i] = 0
        elif pivot_low < win_low:
            leg[i] = 1
        else:
            leg[i] = leg[i - 1]
    return leg

def order_block_indicator(
    df: pd.DataFrame,
    swing_size: int = 50,
    internal_size: int = 5,
    ob_filter: str = ATR_METHOD,
    ob_mitigation: str = HIGHLOW_MITIGATION,
    atr_period: int = 200,
    max_swing_obs: int = 5,
    max_internal_obs: int = 5,
) -> pd.DataFrame:
    """
                  code   open   high    low  close      volume        amount  turnover_rate  internal_ob_1_high  internal_ob_1_low  internal_ob_1_bias  internal_ob_1_strength  internal_ob_2_high  internal_ob_2_low  internal_ob_2_bias  internal_ob_2_strength  internal_ob_3_high  internal_ob_3_low  internal_ob_3_bias  internal_ob_3_strength  internal_ob_4_high  internal_ob_4_low  internal_ob_4_bias  internal_ob_4_strength  internal_ob_5_high  internal_ob_5_low  internal_ob_5_bias  internal_ob_5_strength  swing_ob_1_high  swing_ob_1_low  swing_ob_1_bias  swing_ob_2_high  swing_ob_2_low  swing_ob_2_bias  swing_ob_3_high  swing_ob_3_low  swing_ob_3_bias  swing_ob_4_high  swing_ob_4_low  swing_ob_4_bias  swing_ob_5_high  swing_ob_5_low  swing_ob_5_bias  internal_ob_1_dist_pct  internal_ob_2_dist_pct  internal_ob_3_dist_pct  internal_ob_4_dist_pct  internal_ob_5_dist_pct  swing_trend  trail_top  trail_bottom   high_label   low_label  strong_high  weak_high  strong_low  weak_low  dist_to_strong_low_pct  dist_to_strong_high_pct
    date
    2026-02-26  600588  14.08  14.16  13.91  13.95   497867.80  6.968719e+08         1.4570               15.03              14.57                  -1                      32               16.49              15.36                  -1                       6               12.70              12.24                   1                      33                8.80               8.32                   1                      30               23.54              22.50                  -1                      34            12.70           12.24                1             9.96            9.58                1            28.76           26.84               -1              NaN             NaN                0              NaN             NaN                0               -0.071856               -0.154033                0.139706                0.676683               -0.407392            1      19.01         12.24    weak_high  strong_low          NaN      19.01       12.24       NaN               0.1397058
    2026-02-27  600588  13.96  14.48  13.90  14.22   795810.53  1.132716e+09         2.3290               15.03              14.57                  -1                      32               16.49              15.36                  -1                       6               12.70              12.24                   1                      33                8.80               8.32                   1                      30               23.54              22.50                  -1                      34            12.70           12.24                1             9.96            9.58                1            28.76           26.84               -1              NaN             NaN                0              NaN             NaN                0               -0.053892               -0.137659                0.161765                0.709135               -0.395922            1      19.01         12.24    weak_high  strong_low          NaN      19.01       12.24       NaN               0.1617647
    2026-03-02  600588  13.90  14.05  13.60  13.71   741117.85  1.020875e+09         2.1689               15.03              14.57                  -1                      32               16.49              15.36                  -1                       6               12.70              12.24                   1                      33                8.80               8.32                   1                      30               23.54              22.50                  -1                      34            12.70           12.24                1             9.96            9.58                1            28.76           26.84               -1              NaN             NaN                0              NaN             NaN                0               -0.087824               -0.168587                0.120098                0.647837               -0.417587            1      19.01         12.24    weak_high  strong_low          NaN      19.01       12.24       NaN               0.1200980
    2026-03-03  600588  13.80  13.85  13.11  13.15   727458.63  9.741847e+08         2.1289               15.03              14.57                  -1                      32               16.49              15.36                  -1                       6               12.70              12.24                   1                      33                8.80               8.32                   1                      30               23.54              22.50                  -1                      34            12.70           12.24                1             9.96            9.58                1            28.76           26.84               -1              NaN             NaN                0              NaN             NaN                0               -0.125083               -0.202547                0.074346                0.580529               -0.441376            1      19.01         12.24    weak_high  strong_low          NaN      19.01       12.24       NaN               0.07434641
    2026-03-04  600588  13.01  13.24  12.90  13.05   498681.79  6.513772e+08         1.4594               15.03              14.57                  -1                      32               16.49              15.36                  -1                       6               12.70              12.24                   1                      33                8.80               8.32                   1                      30               23.54              22.50                  -1                      34            12.70           12.24                1             9.96            9.58                1            28.76           26.84               -1              NaN             NaN                0              NaN             NaN                0               -0.131737               -0.208611                0.066176                0.568510               -0.445624            1      19.01         12.24    weak_high  strong_low          NaN      19.01       12.24       NaN               0.06617647
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' not in df.columns:
            raise ValueError("The DataFrame has no 'date' column and no datetime index")
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    df.columns = [c.lower() for c in df.columns]

    n = len(df)
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    volumes = df["volume"].values if "volume" in df.columns else np.ones(n)

    volatility = compute_volatility(df, ob_filter, atr_period)
    parsed_high, parsed_low = compute_parsed_high_low(df, volatility)
    ph_arr = parsed_high.values
    pl_arr = parsed_low.values
    atr_arr = volatility.values

    vol_ma20 = pd.Series(volumes).rolling(20, min_periods=1).mean().values

    swing_leg = compute_legs(highs, lows, swing_size)
    internal_leg = compute_legs(highs, lows, internal_size)

    s_high = np.full((n, max_swing_obs), np.nan)
    s_low = np.full((n, max_swing_obs), np.nan)
    s_bias = np.zeros((n, max_swing_obs), dtype=int)

    i_high = np.full((n, max_internal_obs), np.nan)
    i_low = np.full((n, max_internal_obs), np.nan)
    i_bias = np.zeros((n, max_internal_obs), dtype=int)
    i_strength = np.zeros((n, max_internal_obs), dtype=int)

    sw_trail_top = np.full(n, np.nan)
    sw_trail_bottom = np.full(n, np.nan)
    sw_trend = np.zeros(n, dtype=int)

    bear_src = closes if ob_mitigation == CLOSE_MITIGATION else highs
    bull_src = closes if ob_mitigation == CLOSE_MITIGATION else lows

    swing_obs = []
    internal_obs = []

    ob_state = {
        "swing": {
            "high_level": np.nan, "high_crossed": False, "high_pivot_i": 0,
            "low_level": np.nan, "low_crossed": False, "low_pivot_i": 0,
        },
        "internal": {
            "high_level": np.nan, "high_crossed": False, "high_pivot_i": 0,
            "low_level": np.nan, "low_crossed": False, "low_pivot_i": 0,
        },
    }

    sw_swing_high_level = np.nan
    sw_swing_high_crossed = False
    sw_swing_low_level = np.nan
    sw_swing_low_crossed = False
    sw_cur_trend = 0

    sw_trail_top_val = highs[0]
    sw_trail_bottom_val = lows[0]

    prev_swing_leg = swing_leg[0]
    prev_internal_leg = internal_leg[0]

    def _calc_strength(ob_idx: int) -> int:
        ma20 = vol_ma20[ob_idx]
        vol = volumes[ob_idx]
        vol_ratio = vol / ma20 if ma20 > 0 else 1.0
        vol_score = np.clip((vol_ratio - 1) / (3 - 1), 0, 1) * 60
        ob_width = highs[ob_idx] - lows[ob_idx]
        atr = atr_arr[ob_idx]
        width_ratio = ob_width / atr if atr > 0 else 1.0
        width_score = np.clip(1 - (width_ratio - 0.5) / (2 - 0.5), 0, 1) * 40
        return int(round(vol_score + width_score))

    def _find_ob_bar(pivot_i: int, current_i: int, bias: int) -> dict:
        s = max(0, pivot_i)
        e = max(s + 1, current_i)
        idx = (s + int(np.argmax(ph_arr[s:e]))) if bias == BEARISH \
            else (s + int(np.argmin(pl_arr[s:e])))
        return {
            "high": highs[idx],
            "low": lows[idx],
            "bias": bias,
            "strength": _calc_strength(idx),
        }

    def _mitigate(obs: list, i: int) -> list:
        return [
            ob for ob in obs
            if not (ob["bias"] == BEARISH and bear_src[i] > ob["high"])
               and not (ob["bias"] == BULLISH and bull_src[i] < ob["low"])
        ]

    start = max(swing_size, internal_size)

    for i in range(start, n):

        cur_swing = swing_leg[i]
        if cur_swing != prev_swing_leg:
            pivot_i = i - swing_size
            if cur_swing == 1:
                ob_state["swing"]["low_level"] = lows[pivot_i]
                ob_state["swing"]["low_crossed"] = False
                ob_state["swing"]["low_pivot_i"] = pivot_i
            else:
                ob_state["swing"]["high_level"] = highs[pivot_i]
                ob_state["swing"]["high_crossed"] = False
                ob_state["swing"]["high_pivot_i"] = pivot_i
        prev_swing_leg = cur_swing

        cur_internal = internal_leg[i]
        if cur_internal != prev_internal_leg:
            pivot_i = i - internal_size
            if cur_internal == 1:
                ob_state["internal"]["low_level"] = lows[pivot_i]
                ob_state["internal"]["low_crossed"] = False
                ob_state["internal"]["low_pivot_i"] = pivot_i
            else:
                ob_state["internal"]["high_level"] = highs[pivot_i]
                ob_state["internal"]["high_crossed"] = False
                ob_state["internal"]["high_pivot_i"] = pivot_i
        prev_internal_leg = cur_internal

        for key, obs_list in [("swing", swing_obs), ("internal", internal_obs)]:
            st = ob_state[key]
            if not np.isnan(st["high_level"]) and not st["high_crossed"]:
                if closes[i] > st["high_level"]:
                    st["high_crossed"] = True
                    obs_list.insert(0, _find_ob_bar(st["high_pivot_i"], i, BULLISH))
            if not np.isnan(st["low_level"]) and not st["low_crossed"]:
                if closes[i] < st["low_level"]:
                    st["low_crossed"] = True
                    obs_list.insert(0, _find_ob_bar(st["low_pivot_i"], i, BEARISH))

        swing_obs = _mitigate(swing_obs, i)
        internal_obs = _mitigate(internal_obs, i)

        for slot, ob in enumerate(swing_obs[:max_swing_obs]):
            s_high[i, slot] = ob["high"]
            s_low[i, slot] = ob["low"]
            s_bias[i, slot] = ob["bias"]

        for slot, ob in enumerate(internal_obs[:max_internal_obs]):
            i_high[i, slot] = ob["high"]
            i_low[i, slot] = ob["low"]
            i_bias[i, slot] = ob["bias"]
            i_strength[i, slot] = ob["strength"]

        if swing_leg[i] != (swing_leg[i - 1] if i > 0 else swing_leg[i]):
            pivot_i = i - swing_size
            if swing_leg[i] == 1:
                sw_swing_low_level = lows[pivot_i]
                sw_swing_low_crossed = False
            else:
                sw_swing_high_level = highs[pivot_i]
                sw_swing_high_crossed = False

        if not np.isnan(sw_swing_high_level) and not sw_swing_high_crossed:
            if closes[i] > sw_swing_high_level:
                sw_swing_high_crossed = True
                sw_cur_trend = BULLISH

        if not np.isnan(sw_swing_low_level) and not sw_swing_low_crossed:
            if closes[i] < sw_swing_low_level:
                sw_swing_low_crossed = True
                sw_cur_trend = BEARISH

        sw_trail_top_val = max(sw_trail_top_val, highs[i])
        sw_trail_bottom_val = min(sw_trail_bottom_val, lows[i])

        sw_trail_top[i] = sw_trail_top_val
        sw_trail_bottom[i] = sw_trail_bottom_val
        sw_trend[i] = sw_cur_trend

    for slot in range(max_internal_obs):
        n_str = slot + 1
        df[f"internal_ob_{n_str}_high"] = i_high[:, slot]
        df[f"internal_ob_{n_str}_low"] = i_low[:, slot]
        df[f"internal_ob_{n_str}_bias"] = i_bias[:, slot]
        df[f"internal_ob_{n_str}_strength"] = i_strength[:, slot]

    for slot in range(max_swing_obs):
        n_str = slot + 1
        df[f"swing_ob_{n_str}_high"] = s_high[:, slot]
        df[f"swing_ob_{n_str}_low"] = s_low[:, slot]
        df[f"swing_ob_{n_str}_bias"] = s_bias[:, slot]

    for n_col in range(1, max_internal_obs + 1):
        bias = df[f"internal_ob_{n_col}_bias"]
        ref_price = np.where(
            bias == 1,
            df[f"internal_ob_{n_col}_low"],
            df[f"internal_ob_{n_col}_high"],
        )
        dist = (df["close"] - ref_price) / ref_price
        df[f"internal_ob_{n_col}_dist_pct"] = np.where(bias != 0, dist, np.nan)

    df["swing_trend"] = sw_trend
    df["trail_top"] = sw_trail_top
    df["trail_bottom"] = sw_trail_bottom

    df["high_label"] = np.where(df["swing_trend"] == BEARISH, "strong_high", "weak_high")
    df["low_label"] = np.where(df["swing_trend"] == BULLISH, "strong_low", "weak_low")

    df["strong_high"] = np.where(df["swing_trend"] == BEARISH, df["trail_top"], np.nan)
    df["weak_high"] = np.where(df["swing_trend"] == BULLISH, df["trail_top"], np.nan)
    df["strong_low"] = np.where(df["swing_trend"] == BULLISH, df["trail_bottom"], np.nan)
    df["weak_low"] = np.where(df["swing_trend"] == BEARISH, df["trail_bottom"], np.nan)

    df["dist_to_strong_low_pct"] = np.where(
        df["strong_low"].notna(),
        (df["close"] - df["strong_low"]) / df["strong_low"],
        np.nan,
    )

    df["dist_to_strong_high_pct"] = np.where(
        df["strong_high"].notna(),
        (df["close"] - df["strong_high"]) / df["strong_high"],
        np.nan,
    )

    return df

if __name__ == "__main__":
    from core.util.func import debug_indicator
    debug_indicator(order_block_indicator, symbol="600516", start_date="20250101", end_date="20260516")