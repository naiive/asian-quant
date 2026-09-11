#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from conf.config import STRATEGY_CONFIG
from core.util.func import get_sequence_values, get_squeeze_score, get_anchor_stats, get_count_consecutive

from indicators.adx_indicator import adx_indicator
from indicators.atr_indicator import atr_indicator
from indicators.bollinger_indicator import bollinger_indicator
from indicators.rsi_indicator import rsi_indicator
from indicators.squeeze_momentum_indicator import squeeze_momentum_indicator
from indicators.stc_indicator import stc_indicator
from indicators.support_resistance_indicator import support_resistance_indicator

def run_strategy(df, symbol):
    param_sets = [
        {
            "label": "20-1.8-20-1.5",
            # squeeze_momentum_indicator
            # bollinger_indicator
            "bb_length": 20,
            "bb_mult": 1.8,
            "kc_length": 20,
            "kc_mult": 1.5,
            "use_true_range": True,
            "min_sqz_bars": 4,
            # stc_indicator
            "stc_length": 80,
            "stc_fast_length": 27,
            "stc_slow_length": 50,
            "stc_factor": 0.5,
            # ema_indicator
            "ema_length": 250,
            # support_resistance_indicator
            "srb_left": 15,
            "srb_right": 15,
            # adx_di_indicator
            "adx_length": 14,
            "adx_threshold": 25,
            # atr_indicator
            "atr_length": 14,
            "atr_mult": 1.0,
            "atr_smooth": "RMA",
            # rsi_indicator
            "rsi_length": 14,
            "rsi_ma_length": 14,
            "rsi_smooth": "SMA",
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
        bb_length = p["bb_length"]
        bb_mult = p["bb_mult"]
        kc_length = p["kc_length"]
        kc_mult = p["kc_mult"]
        use_true_range = p["use_true_range"]
        min_sqz_bars = p["min_sqz_bars"]
        stc_length = p["stc_length"]
        stc_fast_length = p["stc_fast_length"]
        stc_slow_length = p["stc_slow_length"]
        stc_factor = p["stc_factor"]
        ema_length = p["ema_length"]
        srb_left = p["srb_left"]
        srb_right = p["srb_right"]
        adx_length = p["adx_length"]
        adx_threshold = p["adx_threshold"]
        atr_length = p["atr_length"]
        atr_mult = p["atr_mult"]
        atr_smooth = p["atr_smooth"]
        rsi_length = p["rsi_length"]
        rsi_ma_length = p["rsi_ma_length"]
        rsi_smooth = p["rsi_smooth"]

        # ==================================================
        # r&s
        # ==================================================
        df = support_resistance_indicator(df, left_bars=srb_left, right_bars=srb_right)
        srb_resistance = df.iloc[-1]['srb_res']
        if df.iloc[-1]['close'] < srb_resistance:
            return None

        # ==================================================
        # sqz
        # ==================================================
        df = squeeze_momentum_indicator(df, length=bb_length, mult=bb_mult, length_kc=kc_length, mult_kc=kc_mult, use_true_range=use_true_range)
        sec_sqz = df.iloc[-3]
        pre_sqz = df.iloc[-2]
        cur_sqz = df.iloc[-1]
        sec_sqz_status = sec_sqz['sqz_status']
        pre_sqz_status = pre_sqz['sqz_status']
        cur_sqz_status = cur_sqz['sqz_status']
        pre_sqz_hcolor = pre_sqz['sqz_hcolor']
        cur_sqz_hcolor = cur_sqz['sqz_hcolor']
        sec_sqz_id = sec_sqz['sqz_id']
        pre_sqz_id = pre_sqz['sqz_id']
        pre_sqz_hcolor_id = pre_sqz['sqz_hcolor_id']

        # ==================================================
        # sqz condition
        # ==================================================
        sqz_cond_1 = (
            cur_sqz_hcolor == 'lime'
            and cur_sqz_status == 'off'
            and pre_sqz_status == 'on'
            and pre_sqz_id >= min_sqz_bars
        )
        sqz_cond_2 = (
            cur_sqz_hcolor == 'lime'
            and cur_sqz_status == 'off'
            and pre_sqz_hcolor == 'lime'
            and pre_sqz_status == 'off'
            and sec_sqz_status == 'on'
            and sec_sqz_id >= min_sqz_bars
        )
        sqz_cond_3 = (
            cur_sqz_hcolor == 'lime'
            and pre_sqz_hcolor in ('maroon', 'green')
            and pre_sqz_status == 'off'
            and pre_sqz_id >= min_sqz_bars
            and pre_sqz_hcolor_id >= min_sqz_bars
        )

        consecutive_off_lime = get_count_consecutive(df.tail(20))
        off_lime_start_idx = len(df) - consecutive_off_lime - 1
        pre_off_lime_row = df.iloc[off_lime_start_idx] if off_lime_start_idx >= 0 else None

        sqz_cond_4 = (
            df.iloc[-2]['close'] < srb_resistance
            and cur_sqz_status == 'off'
            and cur_sqz_hcolor == 'lime'
            and consecutive_off_lime <= 1
            and pre_off_lime_row is not None
            and pre_off_lime_row['sqz_status'] == 'on'
            and pre_off_lime_row['sqz_id'] >= min_sqz_bars
        )

        close_t2 = df.iloc[-2]['close']
        close_t4 = df.iloc[-5]['close']
        close_t5 = df.iloc[-6]['close']
        close_t6 = df.iloc[-7]['close']
        up_resistance_count = sum([close_t4 > srb_resistance, close_t5 > srb_resistance, close_t6 > srb_resistance])

        if sqz_cond_1 and up_resistance_count == 0:
            release = '压力释放'
        elif sqz_cond_2 and up_resistance_count == 0 and srb_resistance > close_t2:
            release = '压力慢放'
        elif sqz_cond_3:
            release = '一直释放'
        elif sqz_cond_4:
            release = '已过亮绿'
        else:
            return None

        # ==================================================
        # ema
        # ==================================================
        ema_series = df['close'].rolling(ema_length).mean()
        ema_val = ema_series.iloc[-1]
        if ema_val > df.iloc[-1]['close']:
            return None

        # ==================================================
        # other indicators
        # ==================================================
        df = bollinger_indicator(df)
        df = adx_indicator(df, adx_length=adx_length, adx_threshold=adx_threshold)
        df = atr_indicator(df, atr_length=atr_length, atr_mult=atr_mult, atr_smooth=atr_smooth)
        df = rsi_indicator(df, rsi_length=rsi_length, rsi_ma_length=rsi_ma_length, rsi_smooth=rsi_smooth)
        df = stc_indicator(df, stc_length=stc_length, stc_fast_length=stc_fast_length, stc_slow_length=stc_slow_length, stc_factor=stc_factor)

        final_row = df.iloc[-1]

        summary_str = get_squeeze_score(df, int(pre_sqz_id))
        adx = final_row['adx']
        atr_long_stop = final_row['atr_long_stop']
        rsi = final_row['rsi']

        # ==================================================
        # judge
        # ==================================================
        i_b = "📈rsi" if rsi >= 70 else "📉rsi" if rsi <= 30 else "🗒️rsi"
        e_b = "📈ema" if final_row['close'] > ema_val else "📉ema"
        a_b = "📈adx" if adx > adx_threshold else "📉adx"
        judge_text = f"{e_b}{a_b}{i_b}"

        # ==================================================
        # tsq、rsq、bsa、rpt
        # ==================================================
        price_sequence, trend_sequence, pct_sequence = get_sequence_values(df, 'res')
        bars_since_anchor, range_pct = get_anchor_stats(df, 'res')

        parameters = {
            "sqz": {"bb_length": bb_length, "bb_mult": bb_mult, "kc_length": kc_length, "kc_mult": kc_mult, "use_true_range": use_true_range, "min_sqz_bars": min_sqz_bars},
            "stc": {"stc_length": stc_length, "stc_fast_length": stc_fast_length, "stc_slow_length": stc_slow_length, "stc_factor": stc_factor},
            "ema": {"ema_length": ema_length},
            "rsi": {"rsi_length": rsi_length, "rsi_ma_length": rsi_ma_length, "rsi_smooth": rsi_smooth},
            "adx": {"adx_length": adx_length, "adx_threshold": adx_threshold},
            "r&s": {"srb_left": srb_left, "srb_right": srb_right},
            "atr": {"atr_length": atr_length, "atr_mult": atr_mult, "atr_smooth": atr_smooth}
        }

        return {
            "日期": final_row.name.strftime('%Y-%m-%d'),
            "代码": symbol,
            "现价": round(final_row['close'], 2),
            "涨幅(%)": round(final_row['pct_chg'], 2),
            "成交量": round(final_row['volume'], 0),
            "释放": release,
            "TSQ": trend_sequence,
            "RSQ": pct_sequence,
            "STC": f"{round(final_row['stc'], 2)}[{final_row['stc_trend']}]",
            "BSA": bars_since_anchor,
            "RPT": round(range_pct, 2),
            "PSQ": price_sequence,
            "换手(%)": round(final_row['turnover_rate'], 0),
            "止损": round(atr_long_stop, 2),
            "挤压": pre_sqz_id,
            "判断": judge_text,
            "分数": summary_str,
            "条件": STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES"),
            "参组": p["label"],
            "参数": json.dumps(parameters)
        }

    except Exception as e:
        print(e)