#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import html
import time
import pandas as pd
from typing import Optional, Tuple
from core.map.emoji import hist_emoji_map, break_emoji_map, yn_emoji_map

def parse_histogram_emoji(energy_str):
    if not energy_str:

        return ""

    items = re.findall(r"([^[-]+)\[[^]]+]", str(energy_str))

    recent_states = items[-6:]

    mom_icons = "".join([hist_emoji_map.get(state, "") for state in recent_states])

    return mom_icons

def parse_break_emoji(val) -> str:
    if not val or pd.isna(val):

        return ""

    return "".join(break_emoji_map.get(x, "") for x in str(val).split("-"))

def fmt_pct(val) -> str:
    if val is None or pd.isna(val):

        return "NA"

    return f"{val:+.2f}%"

def build_tv_card(row: pd.Series) -> str:
    def safe_tag(text, tag="code"):
        if text is None or text == "": return ""

        return f"<{tag}>{html.escape(str(text))}</{tag}>"

    name = row.get("名称", "")

    code = str(row.get("代码", ""))

    price = row.get("收盘价", row.get("现价", ""))

    chg = fmt_pct(row.get("涨幅(%)"))

    ytd = f"{f:+.2f}%" if (v := row.get("年涨幅(%)")) and (f := pd.to_numeric(v, errors='coerce')) is not None and pd.notna(f) else None

    turnover = row.get("换手率(%)", "")

    pe = row.get("市盈率(动)", "")

    squeeze_days = row.get("挤压", "")

    judge_text = row.get("判断", "")

    relex_str = row.get("释放", "")

    tsq_str = row.get("TSQ", "")

    rsq_str = row.get("RSQ", "")

    stc_str = row.get("STC", "")

    bsa_str = row.get("BSA", "")

    summary_str = row.get("分数", "")

    paramete_str = row.get("参数", "")

    atr = row.get("止损", "")

    changes = row.get("走势", "")

    ath_val = str(row.get("ATH", "")).strip()

    ath = yn_emoji_map.get("yes") if ath_val == "是" else yn_emoji_map.get("no")

    volume_up_value = str(row.get("放量", "")).strip()

    volume_up = yn_emoji_map.get("yes") if volume_up_value == "是" else yn_emoji_map.get("no")

    hist = parse_histogram_emoji(row.get("动能"))

    brk = parse_break_emoji(row.get("趋势"))

    mv = row.get("总市值(亿)", "")

    date = str(row.get("日期", ""))

    code_str = code

    if code:
        tv_prefix = ""
        if code.startswith("60"):
            tv_prefix = "SSE"
        elif code.startswith(("00", "30")):
            tv_prefix = "SZSE"

        if tv_prefix:
            tv_link = f"https://cn.tradingview.com/chart/?symbol={tv_prefix}%3A{code}"
            code_str = f'<a href="{tv_link}">{html.escape(code)}</a>'

    lines = []
    if date:
        lines.append(f"📅 日期 {safe_tag(date)}")

    if name or code:
        parts = []
        if name:
            parts.append(safe_tag(name))
        if code:
            parts.append(code_str)
        if parts:
            lines.append(f"💹 代码 {' · '.join(parts)}")

    if price:
        content = html.escape(f"{price}({chg})｜放量 {volume_up}")
        lines.append(f"💰 价格 <code>{content}</code>")

    if atr:
        lines.append(f"✂️ 止损 {safe_tag(atr)}")

    if turnover or pe:
        parts = []
        if turnover:
            parts.append(f"🔄 换手 <code>{turnover}</code>")
        if pe and str(pe).strip():
            parts.append(f"<code>PE {pe}</code>")
        if parts:
            lines.append("｜".join(parts))

    # if squeeze_days:
    #     content = html.escape(f"{squeeze_days} 天｜ath {ath}")
    #     lines.append(f"🧨 挤压 <code>{content}</code>")

    # if summary_str:
    #     lines.append(f"💯 分数 {safe_tag(summary_str)}")

    if hist:
        lines.append(f"💥 动能 {hist}")

    if brk:
        lines.append(f"🚀 趋势 {brk}")

    if changes:
        lines.append(f"📊 走势 {changes}")

    if relex_str:
        lines.append(f"🎉 释放 {safe_tag(relex_str)}")

    if tsq_str:
        lines.append(f"📏 压力 {safe_tag(tsq_str)}")

    if rsq_str:
        lines.append(f"📍 阶梯 {safe_tag(rsq_str)}")

    if stc_str:
        lines.append(f"🔄 趋循 {safe_tag(stc_str)}")

    if bsa_str:
        lines.append(f"↔️ 跨度 {safe_tag(bsa_str)}")

    # if judge_text:
    #     lines.append(f"⚖️ 判断 {safe_tag(judge_text)}")

    if mv or ytd:
        parts = []
        if mv and str(mv).strip():
            parts.append(f"🏛 市值 <code>{mv}亿</code>")
        if ytd:
            parts.append(f"<code>年涨 {ytd}</code>")
        if parts:
            lines.append("｜".join(parts))

    # if paramete_str:
    #     p_parts = paramete_str.split("ema", 1)
    #     if len(p_parts) > 1:
    #         part1 = p_parts[0].strip("｜")
    #         part2 = ("ema" + p_parts[1]).strip("｜")
    #         lines.append(f"📍 参数 {safe_tag(part1)}")
    #         lines.append(f"📍 参数 {safe_tag(part2)}")
    #     else:
    #         lines.append(f"📍 参数 {safe_tag(paramete_str.strip('｜'))}")

    return "\n".join(lines)

def build_unified_message(
    df: Optional[pd.DataFrame],
    strategy_name: Optional[str],
    total_cnt: int = 0,
    page_no: int = 1,
    page_cnt: int = 1,
    is_first_page: bool = True,
) -> Tuple[str, str]:

    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    if is_first_page:
        title = f"📈 扫描 <code>{total_cnt}</code> 条信号"
        lines = [
            f"📅 时间 <code>{current_time}</code>",
            f"📂 策略 <code>{strategy_name}</code>",
            "",
            f"📄 页面 <code>{page_no}/{page_cnt}</code>",
            "────────────────",
            "",
        ]
    else:
        title = f"📄 扫描结果 · 第 <code>{page_no}/{page_cnt}</code> 页"
        lines = [
            "────────────────",
            "",
        ]

    if isinstance(df, pd.DataFrame) and not df.empty:
        for _, row in df.iterrows():
            lines.append(build_tv_card(row))
            lines.append("")
    else:
        if is_first_page:
            lines.append("（无信号数据）")

    return title, "\n".join(lines)
