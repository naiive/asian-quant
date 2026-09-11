#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

def get_sequence_values(df: pd.DataFrame, srb_lab: str):
    """根据压力支撑位获取前几个压力支撑位"""
    col = f'srb_{srb_lab}'

    history = df[df['srb_lab'] == srb_lab].tail(4)
    latest_row = df.iloc[[-1]]

    srb_df = pd.concat([history, latest_row])
    srb_df = srb_df[~srb_df[col].duplicated(keep='first')]

    values = srb_df[col].tolist()

    price_sequence = '-'.join(str(round(v, 2)) for v in values)

    trends = []
    pcts = []
    for i in range(1, len(values)):
        direction = '高' if values[i] >= values[i - 1] else '低'
        pct = abs(values[i] / values[i - 1] - 1) * 100
        trends.append(direction)
        pcts.append(f'{pct:.2f}%')

    trend_sequence = '-'.join(trends)
    pct_sequence = '-'.join(pcts)

    return price_sequence, trend_sequence, pct_sequence

def get_anchor_stats(df: pd.DataFrame, srb_lab: str):
    """获取最近压力位/支撑位锚点到信号日的K线统计"""
    signal_loc = len(df) - 1

    anchor_df = df[df['srb_lab'] == srb_lab]
    if len(anchor_df) == 0:
        return None, None

    anchor_idx = anchor_df.index[-1]
    anchor_loc = df.index.get_loc(anchor_idx)
    bars_since_anchor = signal_loc - anchor_loc

    segment = df.iloc[anchor_loc: signal_loc + 1]

    if srb_lab == 'res':
        anchor_price = df.iloc[-1]['srb_res']
        extreme = segment['low'].min()
        range_pct = abs((anchor_price - extreme) / extreme) * 100
    else:
        anchor_price = df.iloc[-1]['srb_sup']
        extreme = segment['high'].max()
        range_pct = abs((extreme - anchor_price) / anchor_price) * 100

    return bars_since_anchor, range_pct

def get_squeeze_score(df: pd.DataFrame, squeeze_count: int) -> str:
    """BB窄幅和水平打分: 窄度分|水平分"""
    segment = df.iloc[-(squeeze_count + 1): -1]

    if segment['bb_bw_rank'].dropna().empty:
        return "SQ-Empty"

    n_score = segment['bb_bw_rank'].mean()

    basis_seg = segment['bb_basis']

    price_range_ratio = (basis_seg.max() - basis_seg.min()) / basis_seg.mean()

    h_score = max(0, min(100, 100 * (1 - (price_range_ratio / 0.005))))

    return f"n {n_score:02.0f}｜s {h_score:02.0f}｜d {price_range_ratio * 100:.2f}%"


def get_count_consecutive(df):
    """从最新bar往前数, 连续 off+lime 的bar数量"""
    count = 0
    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        if row['sqz_status'] == 'off' and row['sqz_hcolor'] == 'lime':
            count += 1
        else:
            break
    return count


def debug_indicator(indicator_fn, symbol: str, start_date: str, end_date: str):
    """调试指标函数：计算指标并打印详细信息"""
    from core.client.mysql import MySQLClient

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)
    pd.set_option("display.max_colwidth", None)

    raw = MySQLClient().fetch_dailys_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    data = indicator_fn(raw)

    print(data)
    print("=" * 50)

    print(type(data.index))
    print("=" * 50)

    for column, value in data.iloc[-1].items():
        print(f"字段: {column:15} | 数值: {value!s:10} | 类型: {type(value)}")

def get_unified_interval(raw_config_val: str) -> str:
    """
    返回值映射：
    - 分钟 -> 'm'
    - 小时 -> 'h'
    - 天   -> 'd'
    - 周   -> 'w'
    - 月   -> 'o'
    - 年   -> 'y'
    """
    if not raw_config_val:
        return "x"

    val = str(raw_config_val).lower().strip()

    interval_map = {
        # 日线家族
        "d": "d", "day": "d", "daily": "d",
        # 周线家族
        "w": "w", "wk": "w", "week": "w", "weekly": "w",
        # 月线家族 (💡 统一指引向 'o')
        "mo": "o", "mon": "o", "month": "o", "monthly": "o",
        # 年线家族
        "y": "y", "yr": "y", "year": "y", "yearly": "y",
        # 小时家族
        "h": "h", "hr": "h", "hour": "h", "hourly": "h",
        # 分钟家族
        "m": "m", "min": "m", "minute": "m"
    }

    pure_letters = "".join(c for c in val if c.isalpha())

    if pure_letters in interval_map:
        return interval_map[pure_letters]

    if "mo" in pure_letters or "o" in pure_letters:
        return "o"
    if "y" in pure_letters:
        return "y"
    if "w" in pure_letters:
        return "w"
    if "d" in pure_letters:
        return "d"
    if "h" in pure_letters:
        return "h"
    if "m" in pure_letters:
        return "m"

    return "x"