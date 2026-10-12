#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from conf.config import STRATEGY_CONFIG

from indicators.mfa_indicator import mfa_indicator

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
            "label": "mfa",
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

        df = mfa_indicator(df)
        pre_row = df.iloc[-2]
        cur_row = df.iloc[-1]

        if timeframe == 'd':
            cur_mfa_color = cur_row['mfa_color'] == 'green'
            cur_mfa_value = cur_row['mfa_value'] < 1
            pre_mfa_value = pre_row['mfa_value'] >= 1
            cur_mfa_all = pre_row['mfa_all'] >= 5

            if not (cur_mfa_color and cur_mfa_value and pre_mfa_value and cur_mfa_all):
                return None
        else:
            cur_mfa_color = cur_row['mfa_color'] == 'green'
            pre_mfa_color = pre_row['mfa_color'] == 'red'
            pre_mfa_streak = pre_row['mfa_streak'] >= 2

            if not (cur_mfa_color and pre_mfa_color and pre_mfa_streak):
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