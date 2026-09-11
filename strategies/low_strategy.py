#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pandas as pd

from indicators.cross_indicator import cross_indicator
from indicators.macd_indicator import macd_indicator
from indicators.rsi_indicator import rsi_indicator
from indicators.kdj_indicator import kdj_indicator
from indicators.cci_indicator import cci_indicator
from indicators.obv_indicator import obv_indicator
from indicators.vol_ratio_indicator import vol_ratio_indicator

def run_strategy(df, symbol):
    # RSI 双周期参数
    rsi_fast_length   = 14      # RSI 主力周期，推荐 9~14
    rsi_slow_length   = 26      # RSI 辅助周期，推荐 21~26
    rsi_smooth = "SMA"          # RSI 平滑类型，通常不平滑 可选：None / SMA / EMA / WMA / RMA

    # KDJ 参数
    kdj_length = 9              # KDJ RSV 统计周期  标准值9，捕捉短中期动量反转
    kdj_signal = 3              # KDJ K/D 平滑周期 标准值3，与 TradingView 默认一致
    kdj_j_oversold = 30         # J值触底上翻的判断阈值 J<30 且开始上翻才算反转信号 可适当放宽至40，但精度下降

    # MACD 参数
    fast_length = 10            # 快线周期。 用于计算短期指数移动平均线（EMA）。数值越小，指标对价格变化越敏感
    slow_length = 21            # 慢线周期。 用于计算长期指数移动平均线（EMA）
    signal_length = 9           # 信号线周期。 该函数中使用的是简单移动平均（SMA）作用于 MACD 线，用来产生信号

    # CCI 参数
    cci_length = 14             # CCI 统计周期 推荐范围：10~20，14与RSI周期对齐
    cci_oversold = -100         # CCI 超卖阈值  波段策略用-100；极强信号可收紧至-150
    cci_smooth = "SMA"          # CCI 平滑类型，不平滑保留灵敏度  可选：None / SMA / EMA / WMA / RMA

    # OBV 参数
    obv_smooth = "EMA"          # OBV 均线平滑类型  推荐 EMA，对近期量能变化更敏感
    obv_ma_length = 20          # OBV 均线周期 20日均线是量能趋势的标准参考
    obv_div_window = 20         # 底背离检测回看窗口（交易日数） 20日覆盖约一个月，捕捉中期底背离

    # 量比 参数
    vol_ma_length = 20          # 量比基准均量周期（分母） 20日均量是行业通用基准
    vol_shrink_thr = 0.7        # 缩量判定阈值（量比） <0.7 视为缩量；<0.5 视为严重缩量 地量见地价，缩量是底部确认的必要条件
    turnover_ref = 60           # 换手率分位参考周期（交易日数） 60日覆盖约一个季度，捕捉季度级别低位
    turnover_low_pct = 0.20     # 换手率低位分位阈值  低于近60日20%分位=极度清淡，浮筹出清

    # CRO 参数
    channel_length = 9
    average_length = 12
    sma_length = 4
    ob_level1 = 60
    ob_level2 = 53
    os_level1 = -60
    os_level2 = -53

    df = rsi_indicator(df, rsi_length=rsi_fast_length, rsi_ma_length=rsi_fast_length, rsi_smooth=rsi_smooth)
    df_rsi26 = rsi_indicator(df.copy(), rsi_length=rsi_slow_length, rsi_ma_length=rsi_slow_length, rsi_smooth=rsi_smooth)
    df['rsi26'] = df_rsi26['rsi']
    df = kdj_indicator(df, kdj_length=kdj_length, kdj_signal=kdj_signal)
    df = macd_indicator(df, fast_length=fast_length, slow_length=slow_length, signal_length=signal_length)
    df = cci_indicator(df, cci_length=cci_length, cci_smooth=cci_smooth)
    df = obv_indicator(df, obv_smooth=obv_smooth, obv_ma_length=obv_ma_length, divergence_window=obv_div_window)
    df = vol_ratio_indicator(df, vol_ma_length=vol_ma_length, shrink_threshold=vol_shrink_thr, turnover_ref_length=turnover_ref, turnover_low_pct=turnover_low_pct)
    df = cross_indicator(df, channel_length=channel_length, average_length=average_length, sma_length=sma_length, ob_level1=ob_level1, ob_level2=ob_level2, os_level1=os_level1, os_level2=os_level2)

    if df is None or len(df) < 2:
        return None

    ma200 = df['close'].rolling(200).mean().iloc[-1]

    final_row = df.iloc[-1]
    pre_row = df.iloc[-2]

    parameters = {
        "rsi": {"rsi_fast_length" : rsi_fast_length, "rsi_slow_length" : rsi_slow_length, "rsi_smooth" : rsi_smooth},
        "kdj": {"kdj_length" : kdj_length, "kdj_signal" : kdj_signal, "kdj_j_oversold": kdj_j_oversold},
        "mcd": {"fast_length": fast_length, "slow_length": slow_length, "signal_length": signal_length},
        "cci": {"cci_length" : cci_length, "cci_oversold": cci_oversold, "cci_smooth" : cci_smooth},
        "obv": {"obv_smooth" : obv_smooth, "obv_ma_length" : obv_ma_length, "obv_div_window": obv_div_window},
        "vol": {"vol_ma_length" : vol_ma_length, "vol_shrink_thr" : vol_shrink_thr, "turnover_ref" : turnover_ref, "turnover_low_pct": turnover_low_pct},
        "cro": {"channel_length": channel_length, "average_length": average_length, "sma_length": sma_length, "ob_level1": ob_level1, "ob_level2": ob_level2, "os_level1": os_level1, "os_level2": os_level2}
    }

    return {
        "日期": final_row.name.strftime('%Y-%m-%d'),
        "代码": symbol,
        "现价": final_row['close'],
        "涨幅(%)": final_row['pct_chg'],
        "成交量": final_row['volume'],
        "换手(%)": final_row['turnover_rate'],
        "RSI14" : round(final_row['rsi'], 2),
        "RSI26" : round(final_row['rsi26'], 2),
        "KDJ_J" : round(final_row['kdj_j'], 2),
        "PRE_KDJ_J" : round(pre_row['kdj_j'], 2),
        "CCI" : round(final_row['cci'], 2),
        "PRE_CCI" : round(pre_row['cci'], 2),
        "OBV背离" : "是" if final_row['obv_divergence'] else "否",
        "量比" : round(final_row['vol_ratio'], 2),
        "缩量": "是" if final_row['vol_shrink'] else "否",
        "绿线": round(final_row['wtc_green'], 2),
        "MA200": round(ma200, 2) if pd.notna(ma200) else None,
        "MA200偏离(%)": round(final_row['close'] / ma200 - 1, 4) * 100 if pd.notna(ma200) else None,
        "参数" : json.dumps(parameters),
        "参组": ''
    }
