#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from conf.config import STRATEGY_CONFIG

from indicators.stc_indicator import stc_indicator
from indicators.mfa_indicator import mfa_indicator
from indicators.surf_indicator import surf_indicator
from indicators.sma_indicator import sma_indicator
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
            "label": "mix",
            # sma_indicator
            "mix_stc_low": 30,
            "mix_recent": 30,
            "mix_mfa_value": 15,
            "n": 20,
            "cc": 1,
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


def _get_sma_period(timeframe):
    if timeframe in ("d", "w"):
        return 200
    elif timeframe == "m":
        return 46
    else:
        return 200


def _run_single(df, symbol, p):
    try:
        timeframe = p["timeframe"]

        if df is None or len(df) < 2:
            return None

        df = stc_indicator(df, stc_length=p["stc_length"], stc_fast_length=p["stc_fast_length"], stc_slow_length=p["stc_slow_length"], stc_factor=p["stc_factor"])
        df = mfa_indicator(df)
        df = surf_indicator(df, timeframe=p["timeframe"])
        df = sma_indicator(df, n=p["n"], cc=p["cc"])
        df = tma_indicator(df, tma_fast_length=p["tma_fast_length"], tma_slow_length=p["tma_slow_length"], tma_vfactor=p["tma_vfactor"])

        cur_row = df.iloc[-1]

        if timeframe == 'd':
            cur_sma_node = cur_row['sma_node'] == 'bull'
            cur_stc_low = cur_row['stc'] <= p['mix_stc_low']
            cur_t3_trend = cur_row['t3_trend'] == 'bull'

            recent = df.tail(p['mix_recent'])
            has_accum = (recent['zone'] == 'accum').any()
            has_mfa_high = (recent['mfa_value'] >= p['mix_mfa_value']).any()

            if not (cur_sma_node and cur_stc_low and cur_t3_trend and has_accum and has_mfa_high):
                return None

        else:
                return None

        if timeframe in ("d", "w"):
            sma_period = 200
        elif timeframe == "m":
            sma_period = 46
        else:
            sma_period = 200

        sma_diff_pct = None
        if len(df) >= sma_period:
            sma_value = df['close'].rolling(window=sma_period).mean().iloc[-1]
            if sma_value and sma_value != 0:
                sma_diff_pct = round((cur_row['close'] - sma_value) / sma_value * 100, 2)

        parameters = {
            "mfa": {"timeframe": timeframe}
        }

        final_row = df.iloc[-1]

        return {
            "日期": final_row.name.strftime('%Y-%m-%d'),
            "代码": symbol,
            "现价": round(final_row['close'], 2),
            "涨幅(%)": round(final_row['pct_chg'], 2),
            "成交量": round(final_row['volume'], 0),
            f"离SMA{sma_period}(%)": sma_diff_pct,
            "条件": STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES"),
            "参组": p["label"],
            "参数": json.dumps(parameters)
        }

    except Exception as e:
        print(e)