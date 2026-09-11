#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from conf.config import STRATEGY_CONFIG
from indicators.utb_indicator import utb_indicator
from indicators.mfa_indicator import mfa_indicator


def run_strategy(df, symbol):
    param_sets = [
        {
            "label": "mfa",
            # ── UTB 指标参数 ──────────────────────────────
            "key_value": 3,      # UTB 灵敏度
            "atr_period": 14,    # ATR 计算周期
            "use_ha": False,     # 是否使用 Heikin-Ashi 蜡烛
            "utb_window": 1,     # UTB buy 信号回看窗口（天）
            # ── 趋势 & 均线过滤 ───────────────────────────
            "ema": 200,          # 均线周期
            "distance": 0.12,    # 最新收盘价与EMA最大偏离比例（12%）
            "trend_period": 150, # 较长周期的趋势回看（如30天）
            "trend_ratio": 0.8,  # 允许趋势期内有小部分天数跌破（如80%天数在线上，容忍洗盘）
            "pullback_days": 10, # 回溯稍长一点的窗口（如10天内），寻找曾经的回踩
            # ── MFA 活跃度过滤 ────────────────────────────
            "recent": 100,       # 统计吸筹活跃天数的回看窗口
            "active": 25,        # 稍微放宽一点吸筹天数（100天内25天，即1/4时间有吸筹）
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
        if len(df) < p["ema"] + 30:
            return None

        key_value = p["key_value"]
        atr_period = p["atr_period"]
        use_ha = p["use_ha"]
        utb_window = p["utb_window"]
        ema = p["ema"]
        distance = p["distance"]
        trend_period = p["trend_period"]
        trend_ratio = p["trend_ratio"]
        pullback_days = p["pullback_days"]
        recent = p["recent"]
        active = p["active"]

        # ── Step 1: 计算基础指标 ─────────────────────────
        df = utb_indicator(df, key_value=key_value, atr_period=atr_period, use_ha=use_ha)
        df["ema"] = df["close"].ewm(span=ema, adjust=False).mean()

        # ── Step 2: 最新价格过滤（必须在 EMA 之上，且不能偏离太远） ──
        last_close = df["close"].iloc[-1]
        last_ema = df["ema"].iloc[-1]

        if last_close < last_ema:
            return None

        distance_pct = (last_close - last_ema) / last_ema
        if distance_pct > distance:
            return None

        # ── Step 3: 窗口内必须出现过 buy 信号 ─────────────
        recent_utb = df.tail(utb_window)
        if not (recent_utb["utb_signal"] == "buy").any():
            return None

        # ── Step 4: 最后一次 buy 之后不能出现 sell 信号 ───
        # 寻找最近一个 buy 信号的相对位置
        buy_indices = recent_utb[recent_utb["utb_signal"] == "buy"].index
        last_buy_idx = buy_indices[-1]
        after_buy = df.loc[last_buy_idx:].iloc[1:]
        if not after_buy.empty and (after_buy["utb_signal"] == "sell").any():
            return None

        # ── Step 5: 趋势过滤（调整原有冲突逻辑） ─────────
        # 过去长期（trend_period）趋势大体向上，满足比例即可，允许穿刺
        trend_close = df["close"].tail(trend_period)
        trend_ema = df["ema"].tail(trend_period)
        above_count = (trend_close > trend_ema).sum()
        if (above_count / trend_period) < trend_ratio:
            return None

        # ── Step 6: 寻找近期的回踩行为 ───────────────────
        # 在 pullback_days 窗口内，价格曾经触碰或跌破过 EMA（洗盘动作）
        # 或者价格极度逼近 EMA（比如间距小于 1%）
        pb_close = df["close"].tail(pullback_days)
        pb_ema = df["ema"].tail(pullback_days)

        is_pulled_back = (pb_close <= pb_ema).any() or ((pb_close - pb_ema) / pb_ema < 0.01).any()
        if not is_pulled_back:
            return None

        # ── Step 7: 计算并过滤 MFA 活跃度 ─────────────────
        df = mfa_indicator(df)
        recent_days = df.tail(recent)
        active_days = int((recent_days["mfa_color"] != "no").sum())
        if active_days < active:
            return None

        final_row = df.iloc[-1]
        max_ratio = round(recent_days["mfa_max_ratio"].max() * 100, 2)
        distance_signed = round(distance_pct * 100, 2)

        ema_series = df["ema"].tail(trend_period)
        ema_slope_pct = round(
            (ema_series.iloc[-1] - ema_series.iloc[0]) / ema_series.iloc[0] * 100, 2
        )

        parameters = {
            "utb": {"key_value": key_value, "atr_period": atr_period, "use_ha": use_ha, "utb_window": utb_window},
            "mfa": {"recent": recent, "active": active},
            "trend": {"ema": ema, "distance": distance, "trend_period": trend_period, "pullback_days": pullback_days}
        }

        return {
            "日期": final_row.name.strftime('%Y-%m-%d') if hasattr(final_row.name, 'strftime') else str(final_row.name),
            "代码": symbol,
            "现价": round(final_row['close'], 2),
            "涨幅(%)": round(final_row['pct_chg'], 2) if 'pct_chg' in final_row else 0.0,
            "成交量": round(final_row['volume'], 0),
            "换手(%)": round(final_row['turnover_rate'], 2) if 'turnover_rate' in final_row else 0.0,
            "吸筹天数": active_days,
            "吸筹强度": f"{max_ratio}%",
            "均线偏离": f"{distance_signed:+.2f}%",
            "均线斜率": f"{ema_slope_pct:+.2f}%",
            "条件": STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES"),
            "参组": p["label"],
            "参数": json.dumps(parameters, ensure_ascii=False)
        }

    except Exception as e:
        print(f"[{symbol}] 策略异常: {e}")
        return None