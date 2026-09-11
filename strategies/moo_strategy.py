#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from conf.config import STRATEGY_CONFIG
from indicators.atd_indicator import atd_indicator
from indicators.mfa_indicator import mfa_indicator
from indicators.rgf_indicator import rgf_indicator
from indicators.squeeze_momentum_indicator import squeeze_momentum_indicator
from indicators.support_resistance_indicator import support_resistance_indicator
from indicators.utb_indicator import utb_indicator
from indicators.atr_indicator import atr_indicator
from indicators.surf_indicator import surf_indicator

from core.util.func import get_sequence_values, get_anchor_stats

_TF_MAP = {
    "1d": "d",
    "1w": "w",
    "1m": "m",
    "1wk": "w",
    "1mo": "m"
}

co_interval = STRATEGY_CONFIG.get("CO_INTERVAL")
uh_interval = STRATEGY_CONFIG.get("UH_INTERVAL")

if co_interval and uh_interval:
    raise ValueError(
        "CO_INTERVAL 和 UH_INTERVAL 同时配置，无法判断使用哪个"
    )
if not co_interval and not uh_interval:
    raise ValueError(
        "CO_INTERVAL 和 UH_INTERVAL 都没配置"
    )

tf = _TF_MAP.get(co_interval or uh_interval)

PARAM_SETS = [
    {
        "label": "参数一",
        # utb_indicator
        "key_value": 2,
        "atr_period": 14,
        "use_ha": False,
        # rgf_indicator
        "rgf_per": 14,
        "rgf_qty": 2.5,
        # atd_indicator
        "coeff": 1,
        "ap": 14,
        # support_resistance_indicator
        "srb_left": 10,
        "srb_right": 10,
        # squeeze_momentum_indicator
        "bb_length": 15,
        "bb_mult": 1.5,
        "kc_length": 15,
        "kc_mult": 1.2,
        "use_true_range": True,
        "min_sqz_bars": 4,
        # atr_indicator
        "atr_length": 14,
        "atr_mult": 1.0,
        # surf_indicator
        "timeframe": tf
    },
    {
        "label": "参数二",
        "key_value": 3,
        "atr_period": 14,
        "use_ha": False,
        "rgf_per": 14,
        "rgf_qty": 3.0,
        "coeff": 1,
        "ap": 14,
        "srb_left": 15,
        "srb_right": 15,
        "bb_length": 20,
        "bb_mult": 1.8,
        "kc_length": 20,
        "kc_mult": 1.5,
        "use_true_range": True,
        "min_sqz_bars": 4,
        "atr_length": 14,
        "atr_mult": 1.0,
        "timeframe": tf
    }
]

def compute_indicators(df, p):
    df = utb_indicator(df, key_value=p["key_value"], atr_period=p["atr_period"], use_ha=p["use_ha"])
    df = rgf_indicator(df, rgf_per=p["rgf_per"], rgf_qty=p["rgf_qty"])
    df = atd_indicator(df, coeff=p["coeff"], ap=p["ap"])
    df = support_resistance_indicator(df, left_bars=p["srb_left"], right_bars=p["srb_right"])
    df = squeeze_momentum_indicator(df, length=p["bb_length"], mult=p["bb_mult"], length_kc=p["kc_length"], mult_kc=p["kc_mult"])
    df = atr_indicator(df, atr_length=p["atr_length"], atr_mult=p["atr_mult"])
    df = mfa_indicator(df)
    df = surf_indicator(df, timeframe=p["timeframe"])
    return df

def _make_result(final_row, pct, signal, symbol, strategy, label, parameters, **extra):
    base = {
        "日期": final_row.name.strftime('%Y-%m-%d %H:%M:%S'),
        "信号": signal,
        "代码": symbol,
        "现价": round(final_row['close'], 2),
        "涨幅": f"{pct * 100:.2f}%",
        "止损": round(final_row['atr_long_stop'], 2) if signal == 'Long' else round(final_row['atr_short_stop'], 2),
        "策略": strategy,
        "参组": label,
        "参数": json.dumps(parameters, ensure_ascii=False),
    }
    base.update(extra)
    return base

def _run_single_utb(df, symbol, p):
    try:
        pre_row = df.iloc[-2]
        cur_row = df.iloc[-1]

        pct = (cur_row['close'] / pre_row['close'] - 1) if pre_row['close'] != 0 else 0.0

        cond_buy = cur_row['utb_signal'] == 'buy'
        cond_sell = cur_row['utb_signal'] == 'sell'

        if not cond_buy and not cond_sell:
            return None

        signal = "Long" if cond_buy else "Short"

        parameters = {
            "utb": {"key_value": p["key_value"], "atr_period": p["atr_period"], "use_ha": p["use_ha"]},
            "r&s": {"srb_left": p["srb_left"], "srb_right": p["srb_right"]},
            "atr": {"atr_length": p["atr_length"], "atr_mult": p["atr_mult"]},
        }

        return _make_result(cur_row, pct, signal, symbol, "utb", p["label"], parameters)

    except Exception as e:
        print(f"[utb:{p['label']}] {e}")

def _run_single_sqz(df, symbol, p):
    try:
        min_sqz_bars = p["min_sqz_bars"]

        cur_row = df.iloc[-1]
        pre_row = df.iloc[-2]

        srb_res = cur_row['srb_res']
        srb_sup = cur_row['srb_sup']

        cur_close = cur_row['close']
        pre_close = pre_row['close']
        pct = (cur_close / pre_close - 1) if pre_close != 0 else 0.0

        pre_sqz_status = pre_row['sqz_status']
        cur_sqz_status = cur_row['sqz_status']
        pre_sqz_hcolor = pre_row['sqz_hcolor']
        cur_sqz_hcolor = cur_row['sqz_hcolor']
        pre_sqz_id = pre_row['sqz_id']
        pre_sqz_hcolor_id = pre_row['sqz_hcolor_id']

        # 买入条件
        buy_cond_1 = (
            cur_sqz_hcolor == 'lime'
            and cur_sqz_status == 'off'
            and pre_sqz_status == 'on'
            and pre_sqz_id >= min_sqz_bars
        )
        buy_cond_2 = (
            cur_sqz_hcolor == 'lime'
            and pre_sqz_hcolor in ('maroon', 'green')
            and pre_sqz_status == 'off'
            and pre_sqz_id >= min_sqz_bars
            and pre_sqz_hcolor_id >= min_sqz_bars
        )
        buy_cond_3 = (
            (df.iloc[-min_sqz_bars:-1]['sqz_hcolor'] == 'lime').all()
            and (df.iloc[-min_sqz_bars:-1]['sqz_status'] == 'off').all()
            and pre_row['close'] < srb_res
        )

        close_t4 = df.iloc[-5]['close']
        close_t5 = df.iloc[-6]['close']
        close_t6 = df.iloc[-7]['close']
        up_res_count = sum([close_t4 > srb_res, close_t5 > srb_res, close_t6 > srb_res])

        if buy_cond_1 and up_res_count == 0:
            buy_release = '压力释放'
        elif buy_cond_2:
            buy_release = '一直释放'
        elif buy_cond_3:
            buy_release = '一直亮绿'
        else:
            buy_release = None

        # 卖出条件
        sell_cond_1 = (
            cur_sqz_hcolor == 'red'
            and cur_sqz_status == 'off'
            and pre_sqz_status == 'on'
            and pre_sqz_id >= min_sqz_bars
        )
        sell_cond_2 = (
            cur_sqz_hcolor == 'red'
            and pre_sqz_hcolor in ('maroon', 'green')
            and pre_sqz_status == 'off'
            and pre_sqz_id >= min_sqz_bars
            and pre_sqz_hcolor_id >= min_sqz_bars
        )
        sell_cond_3 = (
            (df.iloc[-min_sqz_bars:-1]['sqz_hcolor'] == 'red').all()
            and (df.iloc[-min_sqz_bars:-1]['sqz_status'] == 'off').all()
            and pre_row['close'] > srb_sup
        )

        down_sup_count = sum([close_t4 < srb_sup, close_t5 < srb_sup, close_t6 < srb_sup])

        if sell_cond_1 and down_sup_count == 0:
            sell_release = '支撑释放'
        elif sell_cond_2:
            sell_release = '一直释放'
        elif sell_cond_3:
            sell_release = '一直亮红'
        else:
            sell_release = None

        if buy_release and cur_close >= srb_res:
            signal, release, srb_lab = 'Long', buy_release, 'res'
        elif sell_release and cur_close <= srb_sup:
            signal, release, srb_lab = 'Short', sell_release, 'sup'
        else:
            return None

        price_sequence, trend_sequence, pct_sequence = get_sequence_values(df, srb_lab)
        bars_since_anchor, range_pct = get_anchor_stats(df, srb_lab)

        parameters = {
            "sqz": {"bb_length": p["bb_length"], "bb_mult": p["bb_mult"], "kc_length": p["kc_length"], "kc_mult": p["kc_mult"], "min_sqz_bars": p["min_sqz_bars"]},
            "r&s": {"srb_left": p["srb_left"], "srb_right": p["srb_right"]},
            "atr": {"atr_length": p["atr_length"], "atr_mult": p["atr_mult"]},
        }

        return _make_result(
            cur_row,
            pct,
            signal,
            symbol,
            "sqz",
            p["label"],
            parameters,
            释放类型=release,
            支撑压力价格=price_sequence,
            支撑压力趋势=trend_sequence,
            支撑压力涨幅=pct_sequence,
            区间K线数量=bars_since_anchor,
            区间K线振幅=round(range_pct, 2)
        )

    except Exception as e:
        print(f"[sqz:{p['label']}] {e}")

def _run_single_mfa(df, symbol, p):
    try:
        pre_row = df.iloc[-2]
        cur_row = df.iloc[-1]

        pct = (cur_row['close'] / pre_row['close'] - 1) if pre_row['close'] != 0 else 0.0

        cur_mfa_color = cur_row['mfa_color'] == 'green'
        pre_mfa_value = pre_row['mfa_value'] > 1
        cur_mfa_value = cur_row['mfa_value'] <= 1
        cur_mfa_streak = cur_row['mfa_streak'] >= 4
        cur_mfa_all = cur_row['mfa_all'] >= 8

        if not (cur_mfa_color and pre_mfa_value and cur_mfa_value and cur_mfa_streak and cur_mfa_all):
            return None

        signal = "Long"

        parameters = {
            "mfa": {"mfa_all": int(cur_row['mfa_all'])}
        }

        return _make_result(cur_row, pct, signal, symbol, "mfa", p["label"], parameters)

    except Exception as e:
        print(f"[mfa:{p['label']}] {e}")

def _run_single_suf(df, symbol, p):
    try:
        if len(df) < 2:
            return None

        pre_row = df.iloc[-2]
        cur_row = df.iloc[-1]

        pct = (cur_row['close'] / pre_row['close'] - 1) if pre_row['close'] != 0 else 0.0

        pre_zone = pre_row.get('zone')
        cur_zone = cur_row.get('zone')

        if pre_zone == "accum" and cur_zone == 'no':
            signal = "Long"

        elif pre_zone == "distribution" and cur_zone == 'no':
            signal = "Short"

        else:
            return None

        parameters = {
            "suf": {"timeframe": p["timeframe"]}
        }

        return _make_result(cur_row, pct, signal, symbol, "suf", p["label"], parameters)

    except Exception as e:
        print(f"[suf:{p.get('label')}] {e}")
        return None

def _run_single(df, symbol, p):
    df = compute_indicators(df, p)
    runners = [_run_single_utb, _run_single_sqz, _run_single_mfa, _run_single_suf]
    results = [fn(df, symbol, p) for fn in runners]
    return [r for r in results if r is not None]

def run_strategy(df, symbol):
    results = []
    for p in PARAM_SETS:
        res = _run_single(df.copy(), symbol, p)
        results.extend(res)
    return results