#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from conf.config import STRATEGY_CONFIG

from indicators.stc_indicator import stc_indicator
from indicators.surf_indicator import surf_indicator
from indicators.tma_indicator import tma_indicator

def run_strategy(df, symbol):
    if STRATEGY_CONFIG.get("CN_INTERVAL") == "daily":
        tf = "d"
    elif STRATEGY_CONFIG.get("CN_INTERVAL") == "weekly":
        tf = "w"
    elif STRATEGY_CONFIG.get("CN_INTERVAL") == "monthly":
        tf = "m"
    else:
        tf = "n"

    param_sets = [
        {
            "label": "tma",
            # stc_indicator
            "stc_length": 80,
            "stc_fast_length": 27,
            "stc_slow_length": 50,
            "stc_factor": 0.5,
            # tma_indicator
            "tma_fast_length": 5,
            "tma_slow_length": 8,
            "tma_vfactor": 0.618,
            # surf_indicator
            "timeframe": tf
        }
    ]

    results = []
    for p in param_sets:
        res = _run_single(df.copy(), symbol, p)
        if res:
            results.append(res)
    if not results:
        return None

    return results


def _run_single(df, symbol, p):
    try:
        if df is None or len(df) < 2:
            return None

        df = stc_indicator(df, stc_length=p["stc_length"], stc_fast_length=p["stc_fast_length"], stc_slow_length=p["stc_slow_length"], stc_factor=p["stc_factor"])
        df = surf_indicator(df, timeframe=p["timeframe"])
        df = tma_indicator(df, tma_fast_length=p["tma_fast_length"], tma_slow_length=p["tma_slow_length"], tma_vfactor=p["tma_vfactor"])

        pre_row = df.iloc[-2]
        cur_row = df.iloc[-1]

        pre_t3_trend_bear = pre_row['t3_trend'] == 'bear'
        cur_t3_trend_bull = cur_row['t3_trend'] == 'bull'
        cur_stc_low = cur_row['stc'] <= 30
        cur_stc_trend_bull = cur_row['stc_trend'] == 'bull'

        if not (pre_t3_trend_bear and cur_t3_trend_bull and cur_stc_low and cur_stc_trend_bull):
            return None

        final_row = df.iloc[-1]

        return {
            "日期": final_row.name.strftime('%Y-%m-%d'),
            "代码": symbol,
            "现价": round(final_row['close'], 2),
            "涨幅(%)": round(final_row['pct_chg'], 2),
            "成交量": round(final_row['volume'], 0),
            "条件": STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES"),
            "参组": p["label"]
        }

    except Exception as e:
        print(e)