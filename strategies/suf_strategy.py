#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from conf.config import STRATEGY_CONFIG

from indicators.surf_indicator import surf_indicator

def run_strategy(df, symbol):
    tf = None
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
            "label": "suf",
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
        timeframe = p["timeframe"]

        df = surf_indicator(df, timeframe=timeframe)
        pre_suf = df.iloc[-2]
        cur_suf = df.iloc[-1]
        pre_zone = pre_suf.get('zone')
        cur_zone = cur_suf.get('zone')

        if not (pre_zone == "accum" and cur_zone == 'no'):
            return None

        final_row = df.iloc[-1]

        parameters = {
            "suf": {"timeframe": timeframe}
        }

        return {
            "日期": final_row.name.strftime('%Y-%m-%d'),
            "代码": symbol,
            "现价": round(final_row['close'], 2),
            "涨幅(%)": round(final_row['pct_chg'], 2),
            "成交量": round(final_row['volume'], 0),
            "条件": STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES"),
            "参组": p["label"],
            "参数": json.dumps(parameters)
        }

    except Exception as e:
        print(e)