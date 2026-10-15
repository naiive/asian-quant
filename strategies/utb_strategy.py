#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from conf.config import STRATEGY_CONFIG
from indicators.utb_indicator import utb_indicator
from indicators.stc_indicator import stc_indicator

def run_strategy(df, symbol):
    param_sets = [
        {
            "label": "utb_stc",
            "key_value": 2.4,
            "atr_period": 14,
            "use_ha": False,
            # stc_indicator
            "stc_length": 80,
            "stc_fast_length": 27,
            "stc_slow_length": 50,
            "stc_factor": 0.5,
        }
    ]

    results = []
    for p in param_sets:
        res = _run_single(df.copy(), symbol, p)
        if res:
            results.append(res)
    return results if results else None

def _run_single(df, symbol, p):
    try:

        key_value = p["key_value"]
        atr_period = p["atr_period"]
        use_ha = p["use_ha"]
        stc_length = p["stc_length"]
        stc_fast_length = p["stc_fast_length"]
        stc_slow_length = p["stc_slow_length"]
        stc_factor = p["stc_factor"]

        df = utb_indicator(df, key_value=key_value, atr_period=atr_period, use_ha=use_ha)
        df = stc_indicator(df, stc_length=stc_length, stc_fast_length=stc_fast_length, stc_slow_length=stc_slow_length, stc_factor=stc_factor)

        cur_row = df.iloc[-1]
        cond_buy = cur_row['utb_signal'] == 'buy'
        stc_buy = cur_row['stc'] < 25 and cur_row['stc_trend'] == 'bull'

        if not (cond_buy and stc_buy):
            return None

        final_row = df.iloc[-1]

        parameters = {
            "utb": {"key_value": key_value, "atr_period": atr_period, "use_ha": use_ha},
            "stc": {"stc_length": stc_length, "stc_fast_length": stc_fast_length, "stc_slow_length": stc_slow_length, "stc_factor": stc_factor}
        }

        return {
            "日期": final_row.name.strftime('%Y-%m-%d') if hasattr(final_row.name, 'strftime') else str(final_row.name),
            "代码": symbol,
            "现价": round(final_row['close'], 2),
            "涨幅(%)": round(final_row['pct_chg'], 2) if 'pct_chg' in final_row else 0.0,
            "成交量": round(final_row['volume'], 0),
            "换手(%)": round(final_row['turnover_rate'], 2) if 'turnover_rate' in final_row else 0.0,
            "条件": STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES"),
            "参组": p["label"],
            "参数": json.dumps(parameters, ensure_ascii=False)
        }

    except Exception as e:
        print(f"[{symbol}] 策略异常: {e}")
        return None