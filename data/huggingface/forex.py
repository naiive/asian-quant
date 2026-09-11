#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
from decimal import Decimal
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import logging
import asyncio
import aiohttp
from aiohttp import web
import gradio as gr
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet


# =====================================================
# 0. 配置中心 (CONFIG)
# =====================================================
CONFIG = {
    "watch_list" : ["XAU/USD"],

    "intervals": ["5M", "15M", "1H"],   # 监听的时间周期

    "api": {
        "twelve_data_url": None,        # Twelve Data API Url
        "twelve_data_key": None,        # Twelve Data API Key
        "max_concurrent": 1,            # 免费版建议设为 1 最大进程数
        "kline_limit": 500,             # K线获取数量
        "min_interval": 2               # 串行等待时间 2 秒
    },

    "ui": {
        "ui_name": "FOREX",             # ui列表页标题
        "refresh_interval": 5           # ui日志刷新时间 秒
    },

    "strategy": {
        # 策略路由配置
        "router": {
            "ult": {
                "handler": "_run_ult_strategy",
                "enabled": True,
                "desc": "ult策略"
            },
            "sqz": {
                "handler": "_run_sqz_strategy",
                "enabled": True,
                "desc": "ult策略"
            },
            "rsi": {
                "handler": "_run_rsi_strategy",
                "enabled": True,
                "desc": "rsi策略"
            }
        },

        # indicators不同周期灵敏配置表
        "indicators": {
            "5M": {
                # squeeze_momentum_indicator
                # bollinger_indicator
                "bb_length": 12,        # 布林带周期：计算布林带中轨（SMA）所用的K线根数。数值越小（如12），指标对近期价格波动越敏感；数值越大，指标越平滑但会有滞后
                "bb_mult": 1.5,         # 布林带倍数：决定布林带上下轨的宽度（标准差倍数）。在Squeeze逻辑中，调低这个值（如1.8）会让布林带变窄，从而更容易缩进KC通道内，产生“挤压”信号
                "kc_length": 12,        # 肯特纳通道周期：计算肯特纳通道中轨所用的K线根数。通常建议与 bb_length 保持一致，以确保两者在相同的时间维度下进行波动率对比
                "kc_mult": 1.2,         # 肯特纳通道倍数：决定肯特纳通道的宽度（ATR倍数）。这是控制灵敏度的核心。这个值越小（如1.2），参考框越窄，布林带就越难缩进去，一旦冲出来（灰点）速度会更快
                "use_true_range": True, # 使用真实波幅：是否在计算KC时包含“跳空缺口”（True Range）。设为 True 可以更准确地捕捉因突发消息导致的波动率激增，特别推荐在 1H 或 1D 级别开启
                "min_sqz_bars": 6,      # 最小挤压强度：策略过滤逻辑：要求黑点（Squeeze On）必须连续出现至少 N 根（如6根）

                # ema_indicator
                "ema_length": 21,       # 通常设为 200。它是市场的“多空分水岭”

                # support_resistance_indicator
                "srb_left": 10,         # 在确认一个高点（或低点）时，要求其左侧必须有至少 10 根 K 线比它低（或高）
                "srb_right": 5,         # 在确认一个高点（或低点）时，要求其右侧必须有至少 5 根 K 线比它低（或高）

                # adx_di_indicator
                "adx_length": 14,       # 计算平均趋向指标的时间窗口，通常为 14 根 K 线
                "adx_threshold": 25,    # ADX水平【指标不使用，只是用作判断】

                # atr_indicator
                "atr_length": 14,       # ATR 计算周期
                "atr_mult": 1.0,        # ATR 乘数，用于确定止损距离
                "atr_smooth": "RMA",    # 平滑方式 (RMA, SMA, EMA, WMA)

                # cm_macd_ult_indicator
                "cm_fast_length": 12,   # 快线周期。 用于计算短期指数移动平均线（EMA）。数值越小，指标对价格变化越敏感
                "cm_slow_length": 26,   # 慢线周期。 用于计算长期指数移动平均线（EMA）
                "cm_signal_length": 9,  # 信号线周期。 该函数中使用的是简单移动平均（SMA）作用于 MACD 线，用来产生信号

                # rsi_indicator
                "rsi_length": 14,       # RSI 计算周期。回溯过去 14 个交易日的平均涨跌幅。
                "rsi_ma_length": 14,    # 信号线周期。对 RSI 的结果再进行 14 周期的平滑处理。
                "rsi_smooth": "SMA"     # 平滑方式 (RMA, SMA, EMA, WMA)
            },

            "15M": {
                "bb_length": 12,
                "bb_mult": 1.5,
                "kc_length": 12,
                "kc_mult": 1.2,
                "use_true_range": True,
                "min_sqz_bars": 6,

                "ema_length": 21,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 25,

                "atr_length": 14,
                "atr_mult": 1.0,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            },

            "1H": {
                "bb_length": 12,
                "bb_mult": 1.5,
                "kc_length": 12,
                "kc_mult": 1.2,
                "use_true_range": True,
                "min_sqz_bars": 6,

                "ema_length": 21,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 25,

                "atr_length": 14,
                "atr_mult": 1.0,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            },

            "4H": {
                "bb_length": 12,
                "bb_mult": 1.5,
                "kc_length": 12,
                "kc_mult": 1.2,
                "use_true_range": True,
                "min_sqz_bars": 6,

                "ema_length": 21,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 25,

                "atr_length": 14,
                "atr_mult": 1.0,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            },

            "1D": {
                "bb_length": 20,
                "bb_mult": 2.0,
                "kc_length": 20,
                "kc_mult": 1.7,
                "use_true_range": True,
                "min_sqz_bars": 6,

                "ema_length": 200,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 20,

                "atr_length": 14,
                "atr_mult": 1.0,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            }
        }
    },

    "time": {
        # 市场开盘逻辑分组
        "market_groups": {
            "forex_gold": ["XAU", "OIL", "USD", "EUR", "GBP"],              # 黄金、原油、外汇
            "us_stocks": ["TSLA", "AAPL", "NVDA", "MSFT", "AMZN", "META"]   # 美股
            }
    },

    "notify": {
        "console_enable": True,     # 控制台日志输出
        "wecom_enable": True,       # wecom机器人
        "tg_enable": False,         # telegram bot 发送

        "wecom_webhook": None,      # wecom机器人 webhook
        "tg_token": None,           # telegram token
        "tg_chat_id": None          # telegram chat_id
    }
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
pd.set_option('future.no_silent_downcasting', True)


# =====================================================
# 1. 数据引擎 (DataEngine)
# =====================================================
class DataEngine:
    def __init__(self, cfg: dict, market_cfg: dict):
        self.cfg = cfg
        self.market_cfg = market_cfg
        self.api_url = cfg.get('twelve_data_url')
        self.api_key = cfg.get('twelve_data_key')

        # 频率控制：Twelve Data 免费版 8次/分钟
        self._request_lock = asyncio.Lock()
        self._last_request_time = 0
        self._min_interval = cfg.get('min_interval')
        self._kline_limit = cfg.get('kline_limit')

    async def fetch_klines(self, session: aiohttp.ClientSession, symbol: str, interval) -> Optional[pd.DataFrame]:
        """
        通过 Twelve Data 获取 K 线数据
        """
        # 适配 Twelve Data 周期格式
        interval_lower = interval.lower()

        # 2. 严谨的周期转换映射
        if "m" in interval_lower and "min" not in interval_lower:
            # 处理 "5m" -> "5min", "15m" -> "15min"
            td_interval = interval_lower.replace("m", "min")
        elif "h" in interval_lower:
            # Twelve Data 接受 "1h", "4h" 等格式，确保是小写即可
            td_interval = interval_lower
        elif "d" in interval_lower:
            # 处理 "1d" 或 "1D" -> "1day"
            td_interval = "1day"
        else:
            # 备用：如果没有匹配到，尝试原样输出或给个默认值
            td_interval = interval_lower

        params = {
            "symbol": symbol,
            "interval": td_interval,
            "outputsize": self._kline_limit,
            "apikey": self.api_key,
            "timezone": "Asia/Shanghai"
        }

        # 频率保护：使用 Lock 确保 ScanEngine 并发抓取时自动排队
        async with self._request_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)

            try:
                async with session.get(self.api_url, params=params, timeout=15) as r:
                    self._last_request_time = time.time()

                    if r.status == 429:
                        logger.error("🚨 Twelve Data 触发频率限制，请检查间隔设置")
                        return None

                    res = await r.json()
                    if res.get("status") == "error":
                        logger.error(f"❌ API报错: {res.get('message')}")
                        return None

                    values = res.get('values', [])
                    if not values:
                        return None

                    # 转换为标准 DataFrame
                    df = pd.DataFrame(values)
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df.set_index('datetime', inplace=True)
                    df.index.name = 'date'

                    # 整理列并重排时间（Twelve Data 默认返回最新在前的逆序，需反转）
                    df = df[['open', 'high', 'low', 'close']].astype(float)
                    return df.sort_index()

            except Exception as e:
                logger.error(f"💥 {symbol} 抓取异常: {e}")
                return None


# =====================================================
# 2. 指标引擎 (IndicatorEngine)
# =====================================================
class IndicatorEngine:
    def __init__(self, st_cfg: dict):
        self.cfg = st_cfg

    @staticmethod
    def tv_linreg(series: pd.Series, length: int):
        """线性回归拟合"""
        if pd.isna(series).any() or len(series) < length:
            return np.nan
        x = np.arange(length)
        y_vals = series.values[-length:]  # 确保只取最新长度
        a = np.vstack([x, np.ones(length)]).T
        try:
            m, b = np.linalg.lstsq(a, y_vals, rcond=None)[0]
            return m * (length - 1) + b
        except Exception as e:
            logger.error(f"线性回归拟合失败: {e}")
            return np.nan

    @staticmethod
    def true_range(df: pd.DataFrame) -> pd.Series:
        """计算真实波幅 TR"""
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    @staticmethod
    def add_squeeze_counter(df: pd.DataFrame) -> pd.DataFrame:
        """给每根K线打上一个 连续积压/释放计数"""
        counter = 0
        current_state = None
        sqz_id_list = []
        for status in df["sqz_status"]:
            if status in ["ON", "OFF"]:
                if status == current_state:
                    counter += 1
                else:
                    current_state = status
                    counter = 1
                sqz_id_list.append(counter)
            else:
                current_state = None
                counter = 0
                sqz_id_list.append(0)
        df["sqz_id"] = sqz_id_list
        return df

    @staticmethod
    def get_squeeze_momentum_histogram_color(val, val_prev):
        """动能柱颜色"""
        if pd.isna(val) or pd.isna(val_prev):
            return "数据不足"
        if val > 0:
            return "亮绿" if val > val_prev else "暗绿"
        elif val < 0:
            return "亮红" if val < val_prev else "暗红"
        else:
            return "中性"

    def squeeze_momentum_indicator(self, df: pd.DataFrame, bb_length: int = 20, bb_mult: float = 1.2, kc_length: int = 20, kc_mult: float = 1.2, use_true_range: bool = True) -> pd.DataFrame:
        close, high, low = df['close'], df['high'], df['low']

        # 计算Bollinger Bands (BB)
        # 通过移动平均+标准差计算BB上下轨
        basis = close.rolling(bb_length).mean()
        dev = bb_mult * close.rolling(bb_length).std(ddof=0)
        upper_bb, lower_bb = basis + dev, basis - dev

        # 计算Keltner Channels (KC)
        # 通过ATR或高低差计算KC上下轨
        # 用于判断市场是否处于低波动（挤压）状态
        ma = close.rolling(kc_length).mean()
        r = self.true_range(df) if use_true_range else (high - low)
        rangema = r.rolling(kc_length).mean()
        upper_kc, lower_kc = ma + rangema * kc_mult, ma - rangema * kc_mult

        # 判断Squeeze状态 {"ON":"积压", "OFF":"释放", "NO":无}
        sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
        sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)
        df["sqz_status"] = np.select([sqz_on, sqz_off], ["ON", "OFF"], default="NO")

        # 计算Momentum柱的线性趋势
        highest_h = high.rolling(kc_length).max()
        lowest_l = low.rolling(kc_length).min()
        avg_hl = (highest_h + lowest_l) / 2
        sma_close = close.rolling(kc_length).mean()
        mid = (avg_hl + sma_close) / 2
        source_mid = close - mid
        # 柱状图值大小，0轴上为正，0轴下为负
        histogram_value = source_mid.rolling(kc_length).apply(lambda x: self.tv_linreg(pd.Series(x), kc_length), raw=False)

        # 动能柱数值
        df["sqz_hvalue"] = histogram_value
        # 前一根动能柱数值，用于判断动能柱颜色：亮绿色、绿色、亮红色、红色
        df["sqz_pre_hvalue"] = histogram_value.shift(1)
        # 给每根K线打上一个连续积压或释放计数值，用于判断连续积压
        df = self.add_squeeze_counter(df)

        # 柱状图颜色
        df["sqz_hcolor"] = df.apply(lambda res: self.get_squeeze_momentum_histogram_color(res["sqz_hvalue"], res["sqz_pre_hvalue"]), axis=1)

        # 删除一些中间结果列
        df.drop(columns=["sqz_pre_hvalue"], inplace=True)

        return df

    @staticmethod
    def ema_indicator(df: pd.DataFrame, ema_length: int = 200) -> pd.DataFrame:
        df["ema"] = df['close'].ewm(span=ema_length, adjust=False).mean()

        return df

    @staticmethod
    def support_resistance_indicator(df: pd.DataFrame, srb_left: int = 15, srb_right: int = 15) -> pd.DataFrame:
        # 总窗口长度
        window = srb_left + srb_right + 1

        def is_pivot_high(x):
            mid_val = x[srb_left]
            if mid_val == max(x):
                return mid_val
            return np.nan

        def is_pivot_low(x):
            mid_val = x[srb_left]
            if mid_val == min(x):
                return mid_val
            return np.nan

        df['srb_res'] = df['high'].rolling(window).apply(is_pivot_high, raw=True).ffill()
        df['srb_sup'] = df['low'].rolling(window).apply(is_pivot_low, raw=True).ffill()

        return df

    @staticmethod
    def wilder_smoothing(series: pd.Series, length: int):
        """
        实现 Pine Script 中 ADX/DI 所使用的 Wilder's Smoothing 逻辑。
        SmoothedValue = Prev_SmoothedValue - (Prev_SmoothedValue / length) + CurrentValue
        """
        # 转换为 numpy 数组以便进行迭代计算
        values = series.values
        smoothed = np.empty_like(values)
        smoothed.fill(np.nan)

        # 第一个平滑值设置为前 length 个值的 SMA
        smoothed[length - 1] = np.sum(values[:length])

        # 从第 length 个值开始应用 Wilder's Smoothing
        for i in range(length, len(values)):
            smoothed[i] = smoothed[i - 1] - (smoothed[i - 1] / length) + values[i]

        return pd.Series(smoothed, index=series.index)

    def adx_di_indicator(self, df: pd.DataFrame, adx_length: int = 14, adx_threshold: int = 25 ) -> pd.DataFrame:
        # --- 1. 计算 True Range (TR) ---
        high_low = df['high'] - df['low']
        high_prev_close = np.abs(df['high'] - df['close'].shift(1))
        low_prev_close = np.abs(df['low'] - df['close'].shift(1))

        df['TrueRange'] = high_low.combine(high_prev_close, max).combine(low_prev_close, max)

        # --- 2. 计算 Directional Movement (+DM, -DM) ---
        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']

        # +DM 逻辑: UpMove > DownMove 且 UpMove > 0
        df['adx_plus'] = np.where((up_move > down_move) & (up_move > 0), up_move, 0)

        # -DM 逻辑: DownMove > UpMove 且 DownMove > 0
        df['adx_minus'] = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # --- 3. Wilder's Smoothing (TR, +DM, -DM) ---
        df['SmoothedTR'] = self.wilder_smoothing(df['TrueRange'], adx_length)
        df['SmoothedDMPlus'] = self.wilder_smoothing(df['adx_plus'], adx_length)
        df['SmoothedDMMinus'] = self.wilder_smoothing(df['adx_minus'], adx_length)

        # --- 4. 计算 +DI 和 -DI ---
        # 乘以 100
        df['adx_plus'] = (df['SmoothedDMPlus'] / df['SmoothedTR']) * 100
        df['adx_minus'] = (df['SmoothedDMMinus'] / df['SmoothedTR']) * 100

        # --- 5. 计算 DX (Directional Index) ---
        # DX = |+DI - -DI| / (+DI + -DI) * 100
        # 避免除以零
        sum_di = df['adx_plus'] + df['adx_minus']
        df['DX'] = np.where(sum_di != 0, np.abs(df['adx_plus'] - df['adx_minus']) / sum_di * 100, 0)

        # --- 6. 计算 ADX (DX 的 SMA) ---
        df['adx'] = df['DX'].rolling(window = adx_length).mean()
        df['adx_threshold'] = adx_threshold

        # --- 7. 删除一些中间结果列 ---
        df.drop(columns=['TrueRange', 'SmoothedTR', 'SmoothedDMPlus', 'SmoothedDMMinus', 'DX'], inplace=True)

        return df

    @staticmethod
    def bollinger_indicator(df: pd.DataFrame, bb_length: int = 12, bb_mult: float = 1.8) -> pd.DataFrame:
        # ---------- 1. 基础布林带计算 ----------
        # 中轨 (Basis)
        df['bb_basis'] = df['close'].rolling(window=bb_length).mean()
        # 标准差 (测量值)
        df['bb_std'] = df['close'].rolling(window=bb_length).std()
        # 上下轨 (使用传入的倍数 bb_mult)
        df['bb_upper'] = df['bb_basis'] + (bb_mult * df['bb_std'])
        df['bb_lower'] = df['bb_basis'] - (bb_mult * df['bb_std'])

        # ---------- 2. 计算当前带宽 (BandWidth) ----------
        # 量化绝对窄度
        df['bb_bw'] = (df['bb_upper'] - df['bb_lower']) / df['bb_basis']

        # ---------- 3. 动态排名 (核心修改) ----------
        # pct=True: 返回 0 到 1 之间的百分位
        # ascending=False: 带宽越小(越窄)，排名越靠前，分值越高
        df['bb_bw_rank'] = df['bb_bw'].rank(pct=True, ascending=False) * 100

        return df

    @staticmethod
    def ma_smoothing(series: pd.Series, length: int, method: str) -> pd.Series:
        """
        对序列进行平滑处理，用于 ATR 计算
        """
        method = method.upper()

        # --- SMA（简单移动平均）---
        if method == "SMA":
            return series.rolling(length).mean()

        # --- EMA（指数移动平均）---
        if method == "EMA":
            # adjust=False → 与 TradingView ema() 行为一致
            return series.ewm(span=length, adjust=False).mean()

        # --- RMA（Wilder Moving Average，ATR 默认）---
        if method == "RMA":
            rma = np.full(len(series), np.nan)

            # 数据不足直接返回 NaN
            if len(series) < length:
                return pd.Series(rma, index=series.index)

            # 第一根 RMA = 前 length 根 SMA
            rma[length - 1] = series.iloc[:length].mean()

            alpha = 1 / length
            for i in range(length, len(series)):
                rma[i] = alpha * series.iloc[i] + (1 - alpha) * rma[i - 1]

            return pd.Series(rma, index=series.index)

        # --- WMA（加权移动平均）---
        if method == "WMA":
            weights = np.arange(1, length + 1)

            return series.rolling(length).apply(
                lambda x: np.dot(x, weights) / weights.sum(),
                raw=True,
            )

        raise ValueError(f"Unknown smoothing method: {method}")

    def atr_indicator(self, df: pd.DataFrame, atr_length: int = 14, atr_mult: float = 1.0, atr_smooth: str = "RMA") -> pd.DataFrame:
        # --- True Range ---
        tr = self.true_range(df)

        # --- ATR（TR 平滑）---
        atr = self.ma_smoothing(tr, atr_length, atr_smooth)

        # a = ATR * m | x = ATR * m + high | x2 = low - ATR * m
        df["atr"] = atr
        df["atr_mult"] = atr * atr_mult

        # 空头止损（价格向上突破）
        df["atr_short_stop"] = df["high"] + df["atr_mult"]

        # 多头止损（价格向下跌破）
        df["atr_long_stop"] = df["low"] - df["atr_mult"]

        return df

    @staticmethod
    def cm_macd_ult_indicator(df: pd.DataFrame, cm_fast_length: int = 12, cm_slow_length: int = 26, cm_signal_length: int = 9) -> pd.DataFrame:
        # 1. 计算 MACD 核心数据
        fast_ma = df["close"].ewm(span=cm_fast_length, adjust=False).mean()
        slow_ma = df["close"].ewm(span=cm_slow_length, adjust=False).mean()

        df["cm_macd"] = fast_ma - slow_ma
        # 信号线使用 SMA
        df["cm_signal"] = df["cm_macd"].rolling(window=cm_signal_length).mean()
        df["cm_hist"] = df["cm_macd"] - df["cm_signal"]

        # 2. 计算直方图的 4 色逻辑
        # histA_IsUp: 柱子在0轴上方且增长 (Aqua)
        # histA_IsDown: 柱子在0轴上方且萎缩 (Blue)
        # histB_IsDown: 柱子在0轴下方且增长 (Red)
        # histB_IsUp: 柱子在0轴下方且萎缩 (Maroon)

        df["cm_hist_prev"] = df["cm_hist"].shift(1)

        conditions = [
            (df["cm_hist"] > 0) & (df["cm_hist"] > df["cm_hist_prev"]),   # Aqua
            (df["cm_hist"] > 0) & (df["cm_hist"] <= df["cm_hist_prev"]),  # Blue
            (df["cm_hist"] <= 0) & (df["cm_hist"] < df["cm_hist_prev"]),  # Red
            (df["cm_hist"] <= 0) & (df["cm_hist"] >= df["cm_hist_prev"])  # Maroon
        ]
        choices = ["aqua", "blue", "red", "maroon"]
        df["cm_hist_color"] = np.select(conditions, choices, default="gray")

        # 3. 判定交叉点与延续状态
        df["cm_prev_macd"] = df["cm_macd"].shift(1)
        df["cm_prev_signal"] = df["cm_signal"].shift(1)

        # 判定瞬时交叉点
        df["cm_cross_point"] = 0
        df.loc[(df["cm_prev_macd"] < df["cm_prev_signal"]) & (df["cm_macd"] >= df["cm_signal"]), "cm_cross_point"] = 1
        df.loc[(df["cm_prev_macd"] > df["cm_prev_signal"]) & (df["cm_macd"] <= df["cm_signal"]), "cm_cross_point"] = -1

        # 将 0 替换为 NaN，以便使用 ffill 向前填充最近的一个非零信号
        df["cm_cross_status"] = df["cm_cross_point"].replace(0, np.nan).ffill()
        df["cm_cross_status"] = df["cm_cross_status"].fillna(0).astype(int)

        # 可选：如果在发生第一次交叉前有数据，根据当时 MACD 和 Signal 的相对位置填充初值
        if df["cm_cross_status"].isna().any():
            initial_status = np.where(df["cm_macd"] >= df["cm_signal"], 1, -1)
            df["cm_cross_status"] = df["cm_cross_status"].fillna(pd.Series(initial_status, index=df.index))

        # 清理中间列
        df.drop(columns=["cm_hist_prev", "cm_prev_macd", "cm_prev_signal"], inplace=True)

        return df

    @staticmethod
    def rsi_indicator(df: pd.DataFrame, rsi_length: int = 14, rsi_ma_length: int = 14, rsi_smooth: str = "SMA") -> pd.DataFrame:
        # 计算价格变化
        change = df['close'].diff()

        # 分离涨跌幅 (clipping)
        gain = change.clip(lower=0)
        loss = -change.clip(upper=0)

        # 计算 RMA (Wilder's Moving Average)
        alpha = 1 / rsi_length
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

        # 计算 RSI
        rsi = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
        df["rsi"] = np.where(avg_loss == 0, 100, np.where(avg_gain == 0, 0, rsi))

        # RSI Smoothing MA
        ma_type = rsi_smooth.upper()

        if ma_type == "SMA":
            df["rsi_ma"] = df["rsi"].rolling(rsi_ma_length).mean()

        elif ma_type == "EMA":
            df["rsi_ma"] = df["rsi"].ewm(span=rsi_ma_length, adjust=False).mean()

        elif ma_type == "WMA":
            weights = np.arange(1, rsi_ma_length + 1)
            df["rsi_ma"] = df["rsi"].rolling(rsi_ma_length).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )

        elif ma_type == "RMA":
            df["rsi_ma"] = df["rsi"].ewm(alpha=1 / rsi_ma_length, adjust=False).mean()

        else:
            df["rsi_ma"] = np.nan

        return df

    def calculate(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """综合调用所有指标方法"""
        df = df.copy()

        # 0. 获取不同周期指标参数
        cfg_group = self.cfg.get("indicators", {})
        if interval.upper() not in cfg_group:
            raise ValueError(f"周期【{interval}】不在indicators配置中，请检查配置字典")

        indicators_params = cfg_group[interval.upper()]
        bb_length = int(indicators_params["bb_length"])
        bb_mult = float(indicators_params["bb_mult"])
        kc_length = int(indicators_params["kc_length"])
        kc_mult = float(indicators_params["kc_mult"])
        use_true_range = bool(indicators_params["use_true_range"])

        ema_length = int(indicators_params["ema_length"])

        srb_left = int(indicators_params["srb_left"])
        srb_right = int(indicators_params["srb_right"])

        adx_length = int(indicators_params["adx_length"])
        adx_threshold = int(indicators_params["adx_threshold"])

        atr_length = int(indicators_params["atr_length"])
        atr_mult = float(indicators_params["atr_mult"])
        atr_smooth = indicators_params["atr_smooth"]

        cm_fast_length = int(indicators_params["cm_fast_length"])
        cm_slow_length = int(indicators_params["cm_slow_length"])
        cm_signal_length = int(indicators_params["cm_signal_length"])

        rsi_length = int(indicators_params["rsi_length"])
        rsi_ma_length = int(indicators_params["rsi_ma_length"])
        rsi_smooth = indicators_params["rsi_smooth"]

        # 1. 计算Squeeze
        df = self.squeeze_momentum_indicator(
            df,
            bb_length = bb_length,
            bb_mult = bb_mult,
            kc_length = kc_length,
            kc_mult = kc_mult,
            use_true_range = use_true_range
        )

        # 2. 计算EMA
        df = self.ema_indicator(
            df,
            ema_length = ema_length
        )

        # 3. 计算支撑阻力
        df = self.support_resistance_indicator(
            df,
            srb_left = srb_left,
            srb_right = srb_right
        )

        # 4. 计算ADX
        df = self.adx_di_indicator(
            df,
            adx_length = adx_length,
            adx_threshold = adx_threshold
        )

        # 5. 计算ATR
        df = self.atr_indicator(
            df,
            atr_length = atr_length,
            atr_mult = atr_mult,
            atr_smooth = atr_smooth
        )

        # 6. 计算MACD交叉
        df = self.cm_macd_ult_indicator(
            df,
            cm_fast_length = cm_fast_length,
            cm_slow_length = cm_slow_length,
            cm_signal_length = cm_signal_length
        )

        # 7. 计算RSI
        df = self.rsi_indicator(
            df,
            rsi_length = rsi_length,
            rsi_ma_length = rsi_ma_length,
            rsi_smooth = rsi_smooth
        )

        # 8. 计算BB和窄幅分值
        df = self.bollinger_indicator(
            df,
            bb_length = bb_length,
            bb_mult = bb_mult
        )

        # 9. 计算涨幅
        df['change'] = df['close'].ffill().pct_change()

        return df


# =====================================================
# 3. 策略引擎 (StrategyEngine)
# =====================================================
class StrategyEngine:
    def __init__(self, st_cfg: dict):
        self.cfg = st_cfg
        self._cached_params = {}

        self.strategy_router = {}
        self._init_strategy_router()

    def _init_strategy_router(self):
        """从配置中动态加载策略映射"""
        router_cfg = self.cfg.get("router")

        for strategy_id, info in router_cfg.items():
            if info.get("enabled"):
                handler_name = info.get("handler")
                method = getattr(self, handler_name, None)
                if method:
                    self.strategy_router[strategy_id] = method
                else:
                    logger.error(f"❌ 警告: 配置了策略 {strategy_id} 但未找到方法 {handler_name}")

    def _get_strategy_params(self, interval: str) -> dict:
        """懒加载逻辑（直接返回普通字典）"""
        interval_key = interval.upper()

        # 检查缓存
        if interval_key in self._cached_params:
            return self._cached_params[interval_key]

        p = self.cfg.get("indicators", {}).get(interval_key)
        if not p:
            raise ValueError(f"缺少周期 {interval_key} 的配置，请检查配置文件")

        params = {
            "bb_length": int(p.get("bb_length")),
            "bb_mult": float(p.get("bb_mult")),
            "kc_length": int(p.get("kc_length")),
            "kc_mult": float(p.get("kc_mult")),
            "min_sqz_bars": int(p.get("min_sqz_bars")),

            "srb_left": int(p.get("srb_left")),
            "srb_right": int(p.get("srb_right")),

            "ema_length": int(p.get("ema_length")),

            "adx_length": int(p.get("adx_length")),
            "adx_threshold": int(p.get("adx_threshold")),

            "atr_length": int(p.get("atr_length")),
            "atr_mult": float(p.get("atr_mult")),
            "atr_smooth": p.get("atr_smooth"),

            "cm_fast_length": int(p.get("cm_fast_length")),
            "cm_slow_length": int(p.get("cm_slow_length")),
            "cm_signal_length": int(p.get("cm_signal_length")),

            "rsi_length": int(p.get("rsi_length")),
            "rsi_ma_length": int(p.get("rsi_ma_length")),
            "rsi_smooth": p.get("rsi_smooth")
        }

        self._cached_params[interval_key] = params

        return params

    # BB窄幅和水平打分
    @staticmethod
    def get_bb_squeeze_score(df: pd.DataFrame, squeeze_count: int) -> str:
        """
        排除当前K线，计算前段蓄能。
        输出格式: 窄度分 | 水平分
        """
        # 1. 切片：排除当前线
        segment = df.iloc[-(squeeze_count + 1): -1]

        # 2. 检查有效性
        if segment['bb_bw_rank'].dropna().empty:
            return "SQ-Empty"

        # ---------- A. 窄幅分 (排名分) ----------
        n_score = segment['bb_bw_rank'].mean()

        # ---------- B. 水平分 & 偏离度 ----------
        basis_seg = segment['bb_basis']
        # 计算物理偏离度
        price_range_ratio = (basis_seg.max() - basis_seg.min()) / basis_seg.mean()
        # 计算水平得分 (0.1%以内100分，0.5%以上0分)
        h_score = max(0, min(100, 100 * (1 - (price_range_ratio / 0.005))))

        # 格式说明 100分制
        return f"n {n_score:02.0f} | s {h_score:02.0f} | d {price_range_ratio*100:.2f}%"

    @staticmethod
    def format_price(value, sig_figs=4):
        if value == 0:
            return "0"

        d_val = Decimal(str(value))
        abs_val = abs(d_val)

        if abs_val >= 1:
            precision = 2
        else:
            mag = d_val.adjusted()
            precision = abs(int(mag)) + sig_figs
            precision = min(precision, 20)

        return "{:.{}f}".format(d_val, precision).rstrip('0').rstrip('.')

    @staticmethod
    def _run_ult_strategy(df: pd.DataFrame, strategy_params: dict) -> Dict[str, Any]:
        """策略只返回信号自己特有的字段"""
        _strategy_params = strategy_params

        cur = df.iloc[-1]
        change = cur['change'] * 100

        # 计算前三天的涨幅
        change_t1 = df.iloc[-2]['change']
        change_t2 = df.iloc[-3]['change']
        change_t3 = df.iloc[-4]['change']
        up_days_count = sum([change_t1 > 0, change_t2 > 0, change_t3 > 0])
        down_days_count = sum([change_t1 < 0, change_t2 < 0, change_t3 < 0])

        signal = "no"
        if cur['sqz_status'] == "OFF":

            # --- 做多逻辑：CM金叉 + 暗红柱 ---
            if int(cur['cm_cross_point']) == 1 and cur['sqz_hcolor'] == "暗红":
                # 严苛条件：涨幅大于0，价格在EMA之上，且前三天涨幅最多只有一天
                if change > 0 and cur['close'] > cur['ema'] and up_days_count <= 1:
                    signal = "long"
                else:
                    signal = "watch_long"

            # --- 做空逻辑：CM死叉 + 暗绿柱 ---
            elif int(cur['cm_cross_point']) == -1 and cur['sqz_hcolor'] == "暗绿":
                # 严苛条件：涨幅小于0，价格在EMA之下，且前三天跌幅最多只有一天
                if change < 0 and cur['close'] < cur['ema'] and down_days_count <= 1:
                    signal = "short"
                else:
                    signal = "watch_short"

        # 扩展字段
        changes, changes_str, sqz_status = [], [], []
        for i in range(6, 0, -1):
            change = df.iloc[-(i + 1)]['change'] * 100
            if change > 0:
                status = "涨"
            elif change < 0:
                status = "跌"
            else:
                status = "平"
            changes.append(status)
            changes_str.append(f"{change:+.2f}")
            sqz_status.append(df.iloc[-(i + 1)]['sqz_status'])

        if cur['cm_macd'] > 0:
            cm_macd = '轴上'
        elif cur['cm_macd'] < 0:
            cm_macd = '轴下'
        else:
            cm_macd = '零轴'

        return {
            "signal": signal,
            "extra": {
                "changes": "".join(changes),
                "changes_str": "｜".join(changes_str[-3:]),
                "sqz_status": "".join(sqz_status),
                "macd": cm_macd
            }
        }

    def _run_sqz_strategy(self, df: pd.DataFrame, strategy_params: dict) -> Dict[str, Any]:
        """策略只返回信号字段和自己特有的字段"""
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        change = cur['change'] * 100

        # 前4，5，6天 压力和支撑位的情况
        close_t4 = df.iloc[-5]['close']
        close_t5 = df.iloc[-6]['close']
        close_t6 = df.iloc[-7]['close']
        srb_resistance = df.iloc[-1]['srb_res']
        srb_support = df.iloc[-1]['srb_sup']

        up_resistance_count = sum([close_t4 > srb_resistance, close_t5 > srb_resistance, close_t6 > srb_resistance])
        down_support_count =  sum([close_t4 < srb_support, close_t5 < srb_support, close_t6 < srb_support])

        signal = "no"
        # 基础前提：挤压状态释放，且持续时间足够
        if cur['sqz_status'] == "OFF" and prev['sqz_status'] == "ON" and prev['sqz_id'] >= strategy_params['min_sqz_bars']:

            # --- 做多逻辑分支 ---
            if change > 0 and cur['sqz_hcolor'] == "亮绿":
                # 严苛条件判断，价格在EMA之上，价格突破压力位，前4，5，6天 突破压力位为0天
                if cur['close'] > cur['ema'] and cur['close'] > cur['srb_res'] and up_resistance_count == 0:
                    signal = "long"
                else:
                    signal = "watch_long"

            # --- 做空逻辑分支 ---
            elif change < 0 and cur['sqz_hcolor'] == "亮红":
                # 严苛条件判断，价格在EMA之下，价格跌破支撑位，前4，5，6天 跌破支撑位为0天
                if cur['close'] < cur['ema'] and cur['close'] < cur['srb_sup'] and down_support_count == 0:
                    signal = "short"
                else:
                    signal = "watch_short"

        # 扩展字段
        energy, tr, ts = [], [], []
        for i in range(6, 0, -1):
            row = df.iloc[-(i + 1)]
            energy.append(f"{row['sqz_hcolor']}[{row['sqz_hvalue']:+.4f}]")
            tr.append("高" if row['close'] > cur['srb_res'] else "低")
            ts.append("高" if row['close'] > cur['srb_sup'] else "低")

        # 根据信号返回不同值
        if "long" in signal:
            squeeze_bars = f"{int(prev['sqz_id']):02d}"
            trend = "".join(tr)
            bb_score = self.get_bb_squeeze_score(df, int(prev['sqz_id']))
        elif "short" in signal:
            squeeze_bars = f"{int(prev['sqz_id']):02d}"
            trend = "".join(ts)
            bb_score = self.get_bb_squeeze_score(df, int(prev['sqz_id']))
        else:
            squeeze_bars = "⚪"
            trend = "".join(tr)
            bb_score = "⚪"

        return {
            "signal": signal,
            "extra": {
                "squeeze_bars": squeeze_bars,
                "bb_score": bb_score,
                "energy": "".join(energy),
                "trend": trend
            }
        }

    @staticmethod
    def _run_rsi_strategy(df: pd.DataFrame, strategy_params: dict) -> Dict[str, Any]:
        _strategy_params = strategy_params

        if len(df) < 2:
            return {"signal": "no", "extra": {}}

        rsi_now = df.iloc[-1]['rsi']
        rsi_prev = df.iloc[-2]['rsi']
        direction = "up" if rsi_now > rsi_prev else "down"

        signal = "no"
        rsi_desc = "正常"
        if rsi_now < 20:
            rsi_desc = "极端超卖" if rsi_now < 15 else "严重超卖"
            # 在超卖区且拐头向上时触发执行信号
            signal = "long" if direction == "up" else "watch_long"

        elif rsi_now > 80:
            rsi_desc = "极端超买" if rsi_now > 85 else "严重超买"
            # 在超买区且拐头向下时触发执行信号
            signal = "short" if direction == "down" else "watch_short"

        return {
            "signal": signal,
            "extra": {
                "rsi_info": f"{rsi_desc}（{round(rsi_now, 2)}）{direction}"
            }
        }

    def _standardize_output(self, df: pd.DataFrame, strategy_res: dict, strategy_params: dict, symbol: str, interval: str) -> Dict[str, Any]:
        cur = df.iloc[-1]

        parameters = {
            "sqz": {"bb_length": strategy_params['bb_length'], "bb_mult": strategy_params['bb_mult'], "kc_length": strategy_params['kc_length'], "kc_mult": strategy_params['kc_mult'], "min_sqz_bars": strategy_params['min_sqz_bars']},
            "r&s": {"srb_left": strategy_params['srb_left'], "srb_right": strategy_params['srb_right']},
            "ema": {"ema_length": strategy_params['ema_length']},
            "rsi": {"rsi_length": strategy_params['rsi_length'], "rsi_ma_length": strategy_params['rsi_ma_length'], "rsi_smooth": strategy_params['rsi_smooth']},
            "adx": {"adx_length": strategy_params['adx_length'], "adx_threshold": strategy_params['adx_threshold']},
            "atr": {"atr_length": strategy_params['atr_length'], "atr_mult": strategy_params['atr_mult'], "atr_smooth": strategy_params['atr_smooth']},
            "macd": {"cm_fast_length": strategy_params['cm_fast_length'], "cm_slow_length": strategy_params['cm_slow_length'], "cm_signal_length": strategy_params['cm_signal_length']}
        }

        # 根据信号返回不同值
        if "long" in strategy_res["signal"]:
            atr = self.format_price(cur['atr_long_stop'])
        elif "short" in strategy_res["signal"]:
            atr = self.format_price(cur['atr_short_stop'])
        else:
            atr = "⚪"

        return {
            # 公共字段
            "strategy_name": strategy_res["strategy_name"],                     # 策略名称
            "signal": strategy_res["signal"],                                   # 信号
            "interval": interval,                                               # 周期
            "date": df.index[-1].strftime("%Y-%m-%d"),                          # 日期
            "time": df.index[-1].strftime("%H:%M:%S"),                          # 时间
            "symbol": symbol,                                                   # 代码
            "price": self.format_price(cur['close']),                           # 现格
            "change": round(float(cur['change'] * 100), 2),                     # 涨幅
            "ema": self.format_price(cur['ema']),                               # ema
            "rsi": round(float(cur['rsi']), 4),                                 # rsi
            "adx": round(float(cur['adx']), 4),                                 # adx
            "adx_threshold": int(cur['adx_threshold']),                         # adx基准
            "support": self.format_price(cur['srb_sup']),                       # 支撑
            "resistance": self.format_price(cur['srb_res']),                    # 压力
            "atr_short_stop": self.format_price(cur['atr_short_stop']),         # 做空止损
            "atr_long_stop": self.format_price(cur['atr_long_stop']),           # 做多止损
            "atr": atr,                                                         # 止损
            "parameters": parameters,                                           # 指标参数
            # 扩展字段
            "extra": strategy_res.get("extra", {})
        }

    def execute(self, df: pd.DataFrame, symbol: str, interval: str):
        """
        使用 yield：每跑完一个策略就出一个结果，不中断循环
        """
        strategy_params = self._get_strategy_params(interval)

        for strategy_name, strategy_run in self.strategy_router.items():
            try:
                strategy_res = strategy_run(df, strategy_params)
                if strategy_res is None:
                    continue

                strategy_res["strategy_name"] = strategy_name
                final_res = self._standardize_output(df, strategy_res, strategy_params, symbol, interval)

                yield final_res

            except Exception as e:
                logger.error(f"策略 {strategy_name} 执行异常: {e}")


# =====================================================
# 4. 通知引擎 (NotifyEngine)
# =====================================================
class NotifyEngine:
    def __init__(self, notify_cfg: dict):
        self.cfg = notify_cfg
        self.running_tasks = []

    def process_results(self, results: list, interval: str):
        """不同渠道消息通知：控制台、telegram、企微"""
        results_list = [r for r in results if r is not None]
        if not results_list:
            return

        # 统计产生信号的数量
        signals = [r for r in results_list if r.get('signal') != "no"]

        # 1. 控制台打印
        if self.cfg.get('console_enable'):
            logger.info(f"[{interval}] 扫描完成 | 监控品种: {len(results_list)} | 触发信号: {len(signals)}")
            for item in results_list:
                symbol = item.get('symbol')
                json_str = json.dumps(item, ensure_ascii=False)
                log_prefix = f"[{interval}] {symbol.ljust(20)}"
                if item.get('signal') != "no":
                    logger.info(f"{log_prefix} | Y | {json_str}")
                else:
                    logger.info(f"{log_prefix} | N | {json_str}")

        # 2. Telegram合并发送
        if self.cfg.get('tg_enable') and signals:
            task = asyncio.create_task(self.tg_broadcast_and_send(signals, interval))
            self.running_tasks.append(task)
            task.add_done_callback(lambda t: self.running_tasks.remove(t) if t in self.running_tasks else None)

        # 3. 企业微信通知合并发送
        if self.cfg.get('wecom_enable') and signals:
            task = asyncio.create_task(self.wecom_broadcast_and_send(signals, interval))
            self.running_tasks.append(task)
            task.add_done_callback(lambda t: self.running_tasks.remove(t) if t in self.running_tasks else None)

    # 共用消息卡片组装
    @staticmethod
    def format_single_signal(res, tag):
        """
        将单个信号格式化为字符串片段
        """
        item = MsgUtils.build_row(res)

        strategy_name = item[0]
        interval = item[1].upper()
        date_str = item[2]
        time_str = item[3]
        tv_symbol = item[4].upper().replace("/", "")
        tv_url = item[5][4:-1]
        signal_text = item[6]
        price_str = item[7]
        change_str = f"（{'+' if float(item[8][:-1]) >= 0 else ''}{float(item[8][:-1])}%）"
        atr = item[9]
        judge_text = item[10]

        format_extra = item[11]
        pattern = r'([^: ]+):\s*(.*?)(?=$|\s+[^: ]+:)'
        matches = re.findall(pattern, format_extra)
        extra_map = {k.strip(): v.strip() for k, v in matches}

        squeeze_bars = extra_map.get("挤压", "⚪")
        bb_score = extra_map.get("分数", "⚪")
        energy = extra_map.get("动能", "⚪")
        trend = extra_map.get("趋势", "⚪")
        changes = extra_map.get("走势", "⚪")
        sqz_status = extra_map.get("释放", "⚪")
        macd_sp = extra_map.get("水平", "⚪")
        rsi_info = extra_map.get("强弱", "⚪")

        parameters = json.loads(item[12])

        sqz_data = parameters.get("sqz", {})
        sqz_val = " ".join([f"{sqz_data.get(k)}" for k in ["bb_length", "bb_mult", "kc_length", "kc_mult"] if k in sqz_data])

        rs_data = parameters.get("r&s", {})
        rs_val = " ".join([f"{rs_data.get(k)}" for k in ["srb_left", "srb_right"] if k in rs_data])

        adx_data = parameters.get("adx", {})
        adx_val = " ".join([f"{adx_data.get(k)}" for k in ["adx_threshold"] if k in adx_data])

        ema_data = parameters.get("ema", {})
        ema_val = " ".join([f"{ema_data.get(k)}" for k in ["ema_length"] if k in ema_data])

        atr_data = parameters.get("atr", {})
        atr_val = " ".join([f"{atr_data.get(k)}" for k in ["atr_mult"] if k in atr_data])

        parameters_1 = f"sqz {sqz_val} | r&s {rs_val}"
        parameters_2 = f"adx {adx_val} | ema {ema_val} | atr {atr_val}"

        # 1. 定义不同平台的语法差异
        is_tg = (tag == "telegram")
        is_wecom = (tag == "wecom")

        if not (is_tg or is_wecom):
            logger.error("没有对应的消息卡片，请检查")
            return None

        # 2. 处理 URL 和 样式标签
        # Telegram 用 HTML (<b>, <a>)，WeCom 用 Markdown (**, [])
        link = f'<a href="{tv_url}">{tv_symbol}</a>' if is_tg else f'[{tv_symbol}]({tv_url})'
        b_open = "<b>" if is_tg else ""
        b_close = "</b>" if is_tg else ""
        c_open = "<code>" if is_tg else ""
        c_close = "</code>" if is_tg else ""

        # ult扩展
        is_ult = "ult" in strategy_name.lower()
        ult_block = (
            f"📐 {b_open}水平:{b_close} {macd_sp}\n"
            f"📊 {b_open}走势:{b_close} {changes}\n"
            f"🍃 {b_open}释放:{b_close} {sqz_status}\n"
        ) if is_ult else ""

        # sqz扩展
        is_sqz = "sqz" in strategy_name.lower()
        sqz_block = (
            f"🧨 {b_open}挤压:{b_close} {c_open}{squeeze_bars}{c_close}\n"
            f"💯 {b_open}分数:{b_close} {c_open}{bb_score}{c_close}\n"
            f"📊 {b_open}动能:{b_close} {energy}\n"
            f"🚀 {b_open}趋势:{b_close} {trend}\n"
        ) if is_sqz else ""

        # rsi扩展
        is_rsi = "rsi" in strategy_name.lower()
        rsi_block = (
            f"❄️ {b_open}强弱:{b_close} {rsi_info}\n"
        ) if is_rsi else ""

        # 3. 统一信号模板
        msg_text = (
            f"🎯 {b_open}策略:{b_close} {c_open}{strategy_name}{c_close}\n"
            f"💹 {b_open}代码:{b_close} {b_open}{link}【{interval}】{b_close}\n"
            f"💰 {b_open}价格:{b_close} {c_open}{price_str}{change_str}{c_close}\n"
            f"✂️ {b_open}止损:{b_close} {c_open}{atr}{c_close}\n"
            f"💸 {b_open}信号:{b_close} {c_open}{signal_text}{c_close}\n"
            f"🔄 {b_open}时间:{b_close} {c_open}{time_str}（UTC+8）{c_close}\n"

            # ult扩展
            f"{ult_block}"
            # sqz扩展
            f"{sqz_block}"
            # rsi扩展
            f"{rsi_block}"

            f"⚖️ {b_open}判断:{b_close} {c_open}{judge_text}{c_close}\n"
            f"📅 {b_open}日期:{b_close} {c_open}{date_str}{c_close}\n"
            f"📍 {b_open}参数:{b_close} {c_open}{parameters_1}{c_close}\n"
            f"📍 {b_open}参数:{b_close} {c_open}{parameters_2}{c_close}"
        )

        return msg_text

    # telegram
    async def tg_broadcast_and_send(self, signal_results, interval, tag="telegram"):
        """
        合并信号并分段发送（每 10 个信号合并为一条消息）
        """
        token = self.cfg.get('tg_token')
        chat_id = self.cfg.get('tg_chat_id')
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        chunk_size = 10

        # 记录发送的消息条数
        total_signals = len(signal_results)

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(signal_results), chunk_size):
                chunk = signal_results[i:i + chunk_size]

                # 消息头
                header = (
                    f"🏛️ <b>外汇【{interval.upper()}】周期</b>\n"
                    f"⏰ 扫描时间 {datetime.now().strftime('%H:%M:%S')}\n"
                    f"━━━━━━━━━━━\n"
                )

                body_parts = [self.format_single_signal(res, tag) for res in chunk]

                final_msg = header + "\n\n".join(body_parts)

                payload = {
                    "chat_id": chat_id,
                    "text": final_msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                    "disable_notification": False
                }

                try:
                    async with session.post(url, data=payload, timeout=10) as resp:
                        if resp.status != 200:
                            logger.error(f"TG 发送失败 [{resp.status}]: {await resp.text()}")
                except Exception as e:
                    logger.error(f"TG 网络异常: {e}")

                await asyncio.sleep(0.5)

        logger.info(f"[{interval}] telegram通知发送完毕 | 总信号数: {total_signals}")

    # wecom
    async def wecom_broadcast_and_send(self, signal_results, interval, tag="wecom"):
        """
        wecom 合并信号并分段发送（每 8 个信号合并为一条消息）
        """
        webhook_url = self.cfg.get('wecom_webhook')
        if not webhook_url:
            return

        chunk_size = 8  # wecom 4096 字节限制

        # 记录发送的消息条数
        total_signals = len(signal_results)

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(signal_results), chunk_size):
                chunk = signal_results[i:i + chunk_size]

                header = (
                    f"🏛️ 外汇【{interval.upper()}】周期\n"
                    f"⏰ 扫描时间 {datetime.now().strftime('%H:%M:%S')}\n"
                    f"━━━━━━━━━━━\n"
                )

                body_parts = []
                for res in chunk:
                    text = self.format_single_signal(res, tag)
                    if text:
                        body_parts.append(text.rstrip())

                final_content = header + "\n\n\n".join(body_parts)

                payload = {"msgtype": "markdown", "markdown": {"content": final_content}}

                try:
                    async with session.post(webhook_url, json=payload, timeout=10) as resp:
                        if resp.status != 200:
                            logger.error(f"wecom 发送失败 [{resp.status}]: {await resp.text()}")
                except Exception as e:
                    logger.error(f"wecom 网络异常: {e}")

                await asyncio.sleep(0.5)

        logger.info(f"[{interval}] wecom通知发送完毕 | 总信号数: {total_signals}")

    # 失效通知
    async def send_error_msg(self, error_text: str):
        """当接口失效或无数据时，根据配置发送报警"""
        tasks = []
        # 1. 发送到企业微信
        if self.cfg.get('wecom_enable'):
            webhook_url = self.cfg.get('wecom_webhook')
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"⚠️ **forex系统异常报警**\n\n> 详情: {error_text}\n> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            }
            tasks.append(asyncio.create_task(self._post_request(webhook_url, payload, "wecom_err")))

        # 2. 发送到 Telegram
        if self.cfg.get('tg_enable'):
            token = self.cfg.get('tg_token')
            chat_id = self.cfg.get('tg_chat_id')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": f"⚠️ <b>forex系统异常报警</b>\n\n详情: {error_text}",
                "parse_mode": "HTML"
            }
            tasks.append(asyncio.create_task(self._post_request(url, payload, "tg_err")))

        if tasks:
            await asyncio.gather(*tasks)

    # 心跳通知
    async def send_heartbeat(self):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = (
            f"💓【forex】{now_str}"
        )

        tasks = []
        # 按照配置发送到对应渠道
        if self.cfg.get('wecom_enable'):
            webhook_url = self.cfg.get('wecom_webhook')
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": msg}
            }
            tasks.append(asyncio.create_task(self._post_request(webhook_url, payload, "wecom_hb")))

        if self.cfg.get('tg_enable'):
            token = self.cfg.get('tg_token')
            chat_id = self.cfg.get('tg_chat_id')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            # TG 使用 HTML 格式
            tg_msg = msg.replace("**", "<b>").replace("**", "</b>")
            payload = {
                "chat_id": chat_id,
                "text": tg_msg,
                "parse_mode": "HTML"
            }
            tasks.append(asyncio.create_task(self._post_request(url, payload, "tg_hb")))

        if tasks:
            await asyncio.gather(*tasks)
            logger.info("💓 已发送系统存活心跳通知")

    # 异步POST请求
    @staticmethod
    async def _post_request(url, payload, tag):
        async with aiohttp.ClientSession() as session:
            try:
                if "msgtype" in payload:  # WeCom
                    await session.post(url, json=payload, timeout=5)
                else:  # Telegram
                    await session.post(url, data=payload, timeout=5)
            except Exception as e:
                logger.error(f"发送报警失败 [{tag}]: {e}")


# =====================================================
# 5. 定时引擎 (TimeEngine)
# =====================================================
class TimeEngine:
    def __init__(self, time_cfg: dict):
        self.cfg = time_cfg

    @staticmethod
    def get_wait_seconds(interval: str) -> float:
        now = datetime.now()
        val = int(interval[:-1])
        unit = interval[-1].lower()

        # 1. 先确定延迟偏移量 (单位：秒)
        if unit == 'm':
            offset_sec = 3
        elif unit == 'h':
            offset_sec = 30
        elif unit == 'd':
            offset_sec = 60
        else:
            offset_sec = 5

        # 2. 计算基础对齐时间点 (不带 offset 的整点)
        if unit == 'm':
            target_min = ((now.minute // val) + 1) * val
            if target_min >= 60:
                base_time = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            else:
                base_time = now.replace(minute=target_min, second=0, microsecond=0)

        elif unit == 'h':
            target_hour = ((now.hour // val) + 1) * val
            if target_hour >= 24:
                base_time = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                base_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

        elif unit == 'd':
            base_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if now >= base_time:
                base_time += timedelta(days=1)
        else:
            return 60.0

        # 3. 使用 timedelta 加上偏移量，而不是在 replace 里改 second
        next_run = base_time + timedelta(seconds=offset_sec)

        # 4. 计算差值
        wait_sec = (next_run - now).total_seconds()

        # 如果当前就在延迟窗内（wait_sec 为负），则强制返回 1 秒后执行或跳到下一周期
        return wait_sec if wait_sec > 0 else 1.0

    def is_symbol_market_open(self, symbol: str) -> bool:
        """
        根据配置判断品种是否开盘
        :param symbol: 品种名 (如 XAUUSDm)
        """
        s = symbol.upper()
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute

        # 自动处理夏令时 (3月-11月)
        is_dst = 3 <= now.month <= 11

        # 获取分组配置
        groups = self.cfg.get("market_groups", {})
        forex_keywords = groups.get("forex_gold", [])
        stock_keywords = groups.get("us_stocks", [])

        # --- A. 匹配外汇/黄金逻辑 ---
        if any(k.upper() in s for k in forex_keywords):
            close_h = 5 if is_dst else 6
            open_h = 6 if is_dst else 7
            if (weekday == 5 and hour >= close_h) or weekday == 6:
                return False  # 周六凌晨关盘后或周日
            if weekday == 0 and hour < open_h:
                return False  # 周一凌晨开盘前
            return True

        # --- B. 匹配美股逻辑 ---
        elif any(k.upper() in s for k in stock_keywords):
            if weekday >= 5: return False  # 周六周日不交易

            # 转换北京时间开盘
            start_h, start_m = (21, 30) if is_dst else (22, 30)
            end_h = 4 if is_dst else 5

            curr_min = hour * 60 + minute
            start_min = start_h * 60 + start_m
            end_min = end_h * 60

            # 跨午夜逻辑：21:30以后 OR 凌晨4:00以前
            if curr_min >= start_min or curr_min < end_min:
                return True
            return False

        # --- C. 默认返回 True (防止遗漏品种) ---
        return True


# =====================================================
# 6. 扫描引擎 (ScanEngine)
# =====================================================
class ScanEngine:
    def __init__(self, cfg: dict):
        # 全局运行状态：True正常，False停机
        self.is_active = True
        # 全配置
        self.cfg = cfg
        # 数据引擎
        self.data_e = DataEngine(cfg['api'], cfg['time'])
        # 指标引擎
        self.ind_e = IndicatorEngine(cfg['strategy'])
        # 策略引擎
        self.strat_e = StrategyEngine(cfg['strategy'])
        # 通知引擎
        self.notify_e = NotifyEngine(cfg['notify'])
        # 定时引擎
        self.timer_e = TimeEngine(cfg['time'])
        # UI引擎
        self.ui_e = UIEngine(cfg['ui'])

    async def _proc_symbol(self, session, symbol, interval, sem):
        """单个币种的处理流水线"""
        async with sem:
            try:
                # 【改动点】：传入 time 节点进行开盘检查
                if not self.timer_e.is_symbol_market_open(symbol):
                    # 如果没开盘，直接安静地返回 None，不浪费 API 次数
                    return None

                raw = await self.data_e.fetch_klines(session, symbol, interval)

                if raw is None:
                    logger.error(f"❌ {symbol} 获取数据失败 (API返回空)")
                    return None

                # 1. 检查数据长度
                data_len = len(raw)

                cfg_group = self.cfg['strategy'].get("indicators", {})
                if interval.upper() not in cfg_group: raise ValueError(f"周期【{interval}】不在indicators配置中，请检查配置字典")
                indicators_params = cfg_group[interval.upper()]
                ema_length = int(indicators_params["ema_length"])

                if data_len < ema_length:  # 策略计算 EMA 至少需要 ema_length 条
                    logger.warning(f"⚠️ {symbol} 数据条数不足: {data_len} (需要至少{ema_length}条)")
                    return None

                # 2. 计算指标
                df = self.ind_e.calculate(raw, interval)

                # 3. 执行策略 (注意：此处 res 是一个 Generator)
                res = self.strat_e.execute(df, symbol, interval)
                return res

            except Exception as e:
                logger.error(f"💥 {symbol} 处理过程中崩溃: {e}", exc_info=True)
                return None

    async def scan_cycle(self, session, symbols, interval):
        """单次循环调度：核心逻辑已适配多策略迭代器"""
        sem = asyncio.Semaphore(self.cfg['api']['max_concurrent'])
        tasks = [self._proc_symbol(session, s, interval, sem) for s in symbols]

        # 此时 raw_iterators 是一个包含多个生成器的列表 [<gen>, <gen>, ...]
        raw_iterators = await asyncio.gather(*tasks)

        # --- 核心修改：平铺结果集 ---
        results = []
        for it in raw_iterators:
            if it:
                # 将生成器内容转为 list 并合并到总结果集中
                results.extend(list(it))

        # UI 投喂点
        valid_results = [r for r in results if r is not None]
        signals = [r for r in valid_results if r.get('signal') != "no"]

        try:
            self.ui_e.update_state(valid_results, signals, interval)
        except Exception as ui_err:
            logger.error(f"⚠️ UI 引擎状态更新失败: {ui_err}")

        # 这里的 process_results 内部会过滤没有信号的数据并发送 TG
        self.notify_e.process_results(results, interval)

        # 确保异步任务完成
        if self.notify_e.running_tasks:
            await asyncio.gather(*self.notify_e.running_tasks)

        return valid_results

    async def interval_worker(self, session, interval):
        """
        核心监控工作协程
        :param session: aiohttp 客户端会话
        :param interval: 监控周期，如 '5M', '1H'
        """
        logger.info(f"🟢 [{interval}] 周期监控任务已启动")

        # 1. 状态位初始化
        # last_run_slot: 记录上一次成功执行的时间点（分钟级），防止在同一分钟内重复触发
        last_run_slot = None
        # is_active: 熔断开关。如果接口崩溃，设为 False 以停止后续所有请求
        self.is_active = True

        while True:
            # ==========================================
            # 步骤 A: 熔断检查 (Circuit Breaker)
            # ==========================================
            if not self.is_active:
                logger.critical(f"🛑 [{interval}] 系统已熔断停机。请检查 Token 有效性并手动重启脚本。")
                # 发送停机通知后，退出协程循环，不再占用系统资源
                break

            # ==========================================
            # 步骤 B: 精准定时等待 (Timer)
            # ==========================================
            # 计算距离下一个整点（如 05分, 10分）还剩多少秒
            wait_sec = self.timer_e.get_wait_seconds(interval)
            if wait_sec > 0:
                # 只在长等待时打印日志，避免日志刷屏
                if wait_sec > 10:
                    target_time = (datetime.now() + timedelta(seconds=wait_sec)).strftime('%H:%M:%S')
                    logger.info(f"💤 [{interval}] 下次对齐点: {target_time} (等待 {int(wait_sec)}s)")
                # 无论长短，只要大于0就执行实际的等待
                await asyncio.sleep(wait_sec)

            # ==========================================
            # 步骤 C: 市场开盘状态检查
            # ==========================================
            # 调用之前定义的 is_market_open()，非交易时段不请求接口
            symbols = self.cfg.get("watch_list", [])
            opened_symbols = [s for s in symbols if self.timer_e.is_symbol_market_open(s)]

            if not opened_symbols:
                # 如果当前没有任何一个品种在交易时段（比如周六、周日）
                # 为了省电/省资源，我们每分钟检查一次，并跳过本次循环
                await asyncio.sleep(60)
                continue

            # ==========================================
            # 步骤 D: 重复触发保护
            # ==========================================
            # 确保在同一个 K 线周期内只执行一次扫描
            current_slot = datetime.now().replace(second=0, microsecond=0)
            if last_run_slot == current_slot:
                await asyncio.sleep(1)
                continue

            # ==========================================
            # 步骤 E: 执行核心扫描逻辑
            # ==========================================
            try:
                start_time = time.time()
                symbols = self.cfg.get("watch_list", [])

                if not symbols:
                    logger.warning(f"⚠️ [{interval}] 监控列表为空，跳过本次扫描")
                    await asyncio.sleep(10)
                    continue

                # 1. 并发扫描所有品种
                # 使用信号量控制最大并发数，保护 API 不被封禁
                sem = asyncio.Semaphore(self.cfg['api']['max_concurrent'])
                tasks = [self._proc_symbol(session, s, interval, sem) for s in symbols]

                # gather 会等待所有任务返回。注意：此时 raw_iterators 里的每个元素都是一个生成器对象
                raw_iterators = await asyncio.gather(*tasks)

                # --- 【核心修改点】平铺迭代器结果 ---
                # 以前 results = [dict, dict...]，现在需要把生成器里的内容“倒”出来
                results = []
                for it in raw_iterators:
                    if it is not None:
                        # 将生成器转化为列表并合并到 results 中
                        results.extend(list(it))

                        # 找出【当前应该处于开盘状态】的品种
                opened_symbols = [s for s in symbols if self.timer_e.is_symbol_market_open(s)]

                # 2. 接口可用性检测 (熔断逻辑核心)
                # 过滤出成功获取到数据（非空）的结果
                valid_results = [r for r in results if r is not None]

                # 熔断判定：如果现在有品种该开盘，但我们一个有效结果都没拿到
                # 注意：此处判定依然使用 symbols 原始列表长度，但 results 长度可能因多策略而大于 symbols 长度
                if len(opened_symbols) > 0 and len(valid_results) == 0:
                    self.is_active = False  # 触发熔断开关
                    error_msg = (f"🚨 [{interval}] 所有品种接口请求均失败 \n"
                                 f"结果: 系统已自动熔断停机")

                    logger.critical(error_msg)
                    # 发送报警到配置的通知渠道 (TG/WeCom)
                    await self.notify_e.send_error_msg(error_msg)
                    continue

                # 3. 提取信号用于 UI 信号墙统计
                signals = [r for r in valid_results if r.get('signal') != "no"]
                try:
                    # 传入平铺后的列表，UI 引擎内部会根据策略名区分显示
                    self.ui_e.update_state(valid_results, signals, interval)
                except Exception as ui_err:
                    logger.error(f"⚠️ UI 引擎状态更新失败: {ui_err}")

                # 4. 处理并发送信号通知
                # 传入平铺后的结果列表
                self.notify_e.process_results(results, interval)

                # 5. 确保异步通知任务执行完毕
                if self.notify_e.running_tasks:
                    await asyncio.gather(*self.notify_e.running_tasks)

                # 6. 标记扫描成功
                last_run_slot = current_slot
                duration = time.time() - start_time
                # 日志更新：由于多策略，valid_results 长度可能大于 symbols 数量
                logger.info(
                    f"✅ [{interval}] 扫描完成 (策略行:{len(valid_results)}/品种:{len(symbols)}), 耗时: {duration:.2f}s")

            except Exception as e:
                # 捕获循环内的未知异常，防止单个周期报错导致整个脚本崩溃
                logger.error(f"❌ [{interval}] 运行过程中发生未预料异常: {e}", exc_info=True)
                await asyncio.sleep(10)  # 发生异常时等待 10 秒再试

    async def heartbeat_worker(self):
        """独立的心跳协程：每4小时发送一次存活通知"""
        logger.info("💓 心跳监控协程已启动 (周期: 4小时)")

        # 启动时可以先发一条，确认机器人刚启动是好使的
        await self.notify_e.send_heartbeat()

        while True:
            try:
                # 等待 4 小时 (4 * 3600 秒)
                await asyncio.sleep(4 * 3600)

                # 如果系统没有因为故障停机 (is_active 为 True)，则发送心跳
                if self.is_active:
                    await self.notify_e.send_heartbeat()
                else:
                    logger.warning("💓 心跳跳过: 系统目前处于熔断停机状态")

            except Exception as e:
                logger.error(f"❌ 心跳协程异常: {e}")
                await asyncio.sleep(60)  # 异常后等待一分钟重试

    async def run(self):
        async with aiohttp.ClientSession() as session:
            try:
                logger.info("⚡ 启动即时扫描")

                # 1. 获取 symbols
                symbols = self.cfg.get("watch_list")

                # 2. 检查 symbols 是否有效
                if symbols and len(symbols) > 0:
                    # 执行首次即时扫描
                    await self.scan_cycle(session, symbols, self.cfg.get("intervals")[0])
                else:
                    logger.error("❌ 严重错误: 最终 symbols 列表为空，无法扫描！")

            except Exception as e:
                logger.error(f"❌ 初始扫描发生崩溃: {e}", exc_info=True)

            # 组装所有 worker
            workers = [self.interval_worker(session, i) for i in self.cfg.get('intervals')]

            # 添加心跳 worker
            workers.append(self.heartbeat_worker())

            # 并发运行
            await asyncio.gather(*workers)


# =====================================================
# 7. UI引擎 (UIEngine)
# =====================================================
class UIEngine:
    def __init__(self, ui_cfg: dict):
        self.cfg = ui_cfg
        # 信号墙改为字典存储，按策略分类
        self.signals_by_strategy = {
            "ult": [],
            "sqz": [],
            "rsi": []
        }
        self.market_snapshot = []
        self.last_update = "尚未开始"
        self.log_stream = []

        self.theme_css = """
            /* 容器 */
            .gradio-container { 
                background-color: #f7f9fc !important; 
            }
            
            /* 标题栏集成 */
            .header-wrapper {
                text-align: center !important; 
                padding: 20px 0 !important; 
                background-color: #ffffff !important; 
                border-bottom: 1px solid #e1e4e8 !important; 
                margin-bottom: 20px !important;
            }
            
            .header-title {
                color: #e67e22 !important; 
                margin: 0 !important; 
                font-size: 28px !important; 
                font-weight: 800 !important;
            }
            
            /* 状态栏容器 */
            .stat-card { 
                background: #ffffff !important; 
                padding: 16px !important;
                border-radius: 12px !important;
                border: 1px solid #e1e4e8 !important;
            }
            
            /* 内部 */
            .stat-box, .log-box { 
                background-color: #f0f2f5 !important; 
                color: #0066cc !important; 
                font-family: 'Fira Code', monospace !important; 
                padding: 12px !important;
                border-radius: 8px !important;
                border: 1px solid #d1d5da !important;
                min-height: 100px;
            }
    
            /* 表格美化：亮色模式下的表格 */
            #sig-table-ult, #sig-table-sqz, #sig-table-rsi, #market-table { 
                background: white !important; 
                border-radius: 12px !important; 
                overflow: visible !important; 
            }
    
            #sig-table-ult, #sig-table-sqz, #sig-table-rsi, #market-table {
                max-height: 1200px !important; /* 允许表格在1200像素内滚动 */
                overflow-y: auto !important;   /* 强制开启垂直滚动条 */
                border: 1px solid #e1e4e8 !important;
            }
        """

    def update_state(self, all_results, signal_results, interval):
        """
        all_results: 当前扫描周期内所有币种的完整数据列表 (包含指标)
        signal_results: 触发了 long/short 信号的币种列表
        interval: 当前扫描的周期 (如 '1H')
        """
        # 1. 更新最后刷新时间
        self.last_update = datetime.now().strftime("%H:%M:%S")

        # 2. 更新全市场概览快照 (用于 📊 标签页)
        # 确保每个 item 都带上周期信息，以便 _refresh_logic 识别
        for item in all_results:
            item['interval'] = interval
        self.market_snapshot = all_results

        # 3. 更新信号墙 (按策略分类存储)
        if signal_results:
            for s in signal_results:
                s['interval'] = interval
                strat = s.get('strategy_name').lower()
                # 如果是新策略且不在字典里，可以动态增加
                if strat not in self.signals_by_strategy:
                    self.signals_by_strategy[strat] = []

                # 插入到对应策略列表最前面，并保留100条
                self.signals_by_strategy[strat] = ([s] + self.signals_by_strategy[strat])[:100]

        # 4.生成实时扫描日志
        log_msg = f"[{interval}] 扫描完成 | 时间: {self.last_update} | 信号: {len(signal_results)} | 监控总数: {len(all_results)}"

        # 如果有信号，详细记录一下哪个币出了信号
        if signal_results:
            # 格式示例: BTC(Squeeze), ETH(RSI)
            signal_details = [
                f"{s['symbol'].split('-')[0]}({s.get('strategy_name')})"
                for s in signal_results
            ]
            # 将列表拼接成字符串
            log_msg += f" (发现: {', '.join(signal_details)})"

        # 存入 log_stream，放在最前面（最新的在上面）
        self.log_stream.insert(0, log_msg)
        # 只保留最近 20 条日志
        self.log_stream = self.log_stream[:20]

    def _refresh_logic(self):
        # 1. 信号墙：按策略分别构建行数据
        # 必须按照 create_demo 中【outputs】 的顺序返回
        ult_rows = [MsgUtils.build_row(item) for item in self.signals_by_strategy.get("ult", [])]
        sqz_rows = [MsgUtils.build_row(item) for item in self.signals_by_strategy.get("sqz", [])]
        rsi_rows = [MsgUtils.build_row(item) for item in self.signals_by_strategy.get("rsi", [])]

        # 2. 全市场概览：显示所有快照数据
        market_rows = [MsgUtils.build_row(item) for item in self.market_snapshot if item]

        # 3. 状态栏信息：从快照数据的第一个样本中取时间
        if self.market_snapshot:
            sample = self.market_snapshot[0]
            status_info = f"<span>【{sample.get('interval')}】数据点: {sample.get('date')} {sample.get('time')[:5]} | 刷新时间: {self.last_update}</span>"
        else:
            status_info = f"<span>等待数据同步... | 系统时间: {self.last_update}</span>"

        status_info_html = f"<div class='stat-box'>{status_info}</div>"

        log_html = f"<div class='log-box'>{''.join([f'<div>> {m}</div>' for m in self.log_stream])}</div>"

        # 注意顺序：ult信号, sqz信号, 全市场, 状态, 日志
        return ult_rows, sqz_rows, rsi_rows, market_rows, status_info_html, log_html

    def create_demo(self):
        """
        核心 UI 构建方法
        """
        with gr.Blocks() as demo:

            gr.HTML(f"""<div class="header-wrapper"><h1 class="header-title">{self.cfg.get("ui_name")}看板</h1></div>""")

            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group(elem_classes="stat-card"):
                        gr.Markdown("### ⏳ 最新状态")
                        status_display = gr.HTML(value="<div class='stat-box'>>> 等待扫描...</div>")

                with gr.Column(scale=3):
                    with gr.Group(elem_classes="stat-card"):
                        gr.Markdown("### 🔄 扫描日志")
                        log_display = gr.HTML(value="<div class='log-box'>>> 系统启动中...</div>")

            # 信号墙 和 全市场 数据Tab
            table_headers = ["策略",  "周期",  "日期",   "时间", "代码",   "图表",  "信号",   "现价",  "涨幅",  "止损",  "判断",   "其他",  "参数"]
            # 信号墙 和 全市场，不给最后一个宽度，让它自己撑开
            column_widths = ["100px", "60px", "120px", "80px", "150px", "60px", "100px", "120px", "80px", "120px", "240px", "600px",     ]

            with gr.Tabs(elem_classes="tabs"):
                # 将信号墙拆分为多个 Tab
                with gr.TabItem("🔥 ult信号"):
                    ult_table = gr.DataFrame(
                        headers=table_headers,
                        column_widths=column_widths,
                        datatype="markdown",
                        elem_id="sig-table-ult",
                        wrap=False,
                        interactive=True,
                        max_height=1000,
                        row_count=200,
                        show_row_numbers=True
                    )
                with gr.TabItem("🎯 sqz信号"):
                    sqz_table = gr.DataFrame(
                        headers=table_headers,
                        column_widths=column_widths,
                        datatype="markdown",
                        elem_id="sig-table-sqz",
                        wrap=False,
                        interactive=True,
                        max_height=1000,
                        row_count=200,
                        show_row_numbers=True
                    )
                with gr.TabItem("❄️ rsi信号"):
                    rsi_table = gr.DataFrame(
                        headers=table_headers,
                        column_widths=column_widths,
                        datatype="markdown",
                        elem_id="sig-table-rsi",
                        wrap=False,
                        interactive=True,
                        max_height=1000,
                        row_count=200,
                        show_row_numbers=True
                    )
                with gr.TabItem("📊 全市场"):
                    market_table = gr.DataFrame(
                        headers=table_headers,
                        column_widths=column_widths,
                        datatype="markdown",
                        elem_id="market-table",
                        wrap=False,
                        interactive=True,
                        max_height=1000,
                        row_count=200,
                        show_row_numbers=True
                    )

            # 设置5秒定时刷新
            gr.Timer(self.cfg.get("refresh_interval", 5)).tick(
                fn=self._refresh_logic,
                outputs=[ult_table, sqz_table, rsi_table, market_table, status_display, log_display]
            )

        # 把 css 挂载到 demo 对象上，方便其他引擎读取
        demo.custom_css = self.theme_css

        return demo


# =====================================================
# 8. 启动引擎 (RunEngine)
# =====================================================
class RunEngine:
    def __init__(self, config: Dict):
        # 1. 自动处理时区
        self._setup_timezone()

        # 2. 动态加载配置
        self.config = config

        # 3. 获取配置
        self.local_key = self._load_initial_config()
        self.env_key = os.getenv("ENCRYPTION_KEY")
        self.final_key = self.env_key or self.local_key

        if not self.final_key:
            raise ValueError("CRITICAL: ENCRYPTION_KEY not found!")

        # 4. 初始化加密对象
        self.cipher = Fernet(self.final_key.encode())

        # 5. 解密并更新配置
        self._setup_credentials()

        # 6. 初始化引擎实例
        self.scan_engine = ScanEngine(self.config)

    @staticmethod
    def _setup_timezone():
        os.environ['TZ'] = 'Asia/Shanghai'
        if hasattr(time, 'tzset'):
            time.tzset()

    @staticmethod
    def _load_initial_config():
        try:
            from conf.config import ENCRYPTION_KEY as LOCAL_VAL
            return LOCAL_VAL
        except (ImportError, ModuleNotFoundError):
            logger.warning("⚠️ Local config file not found. Switching to Environment Mode.")
            return None

    def _setup_credentials(self):
        try:
            twelve_data_url = b'gAAAAABpX2App_DGAktBZLYAxKvv8WYTZgDagkxRPd_PKauN_VSBSeAIV3NYxEAJIvsSJ1eS76OWY_I-59Kym3TFhuEun39CywUmSm2wPuVjGmHNwgqDUrqYzRhdcoTw_wM2EnCC62k4'
            twelve_data_key = b'gAAAAABpX1jAwrYOW4EGBhuRwrU7Iz8s_tfJssQ0-yzCEOWoAVzG-4enR4wW1lxyBiqFc7N0k8HmdqBkiRj8SVoCmw5khSOq4vRX1hJDuRaYqylrT3NYq7XJ609kGEr11DrMAPXEWbFQ'
            wecom_webhook = b'gAAAAABpX1lf_OZccl6JYh14FJlLEmJDtV37L1jW5MMRhdA09xypIujad5g1e2axJUwOA_gKCF3kodoYVG9Wrj1TyayLXmSn3t6lnG5xzNXedE01dNq1E-S77oYFLhaS9g3Ay24P2apcvBGkaV61cI76Pk7jNrjRTNjhxwgrvT3FiDHaQk3FULbFwvQJy0BADgv1cli4_vzB'
            tg_token = b'gAAAAABpX1mGV2Aqsf_W0eXjohhjNzWB4pDhsPqRDDei9jfKMkwsCT9Bu0qHzOGDAaapiBGNPwP1hyk46SN78yq2si5RylJTSBmdh6wPJlWpeAZtlEgu7wuxlEi3AMByECDdWnBx1iol'
            tg_chat_id = b'gAAAAABpX1maZKmpePVf4ancQG2QpOX7YXk4wPMqPTw8x4DgJN3cKaVO6I0cQp0eCpL1gR4lim2W6k0LWXqH-R28889G2I446Q=='

            self.config["api"]["twelve_data_url"] = self.cipher.decrypt(twelve_data_url).decode()
            self.config["api"]["twelve_data_key"] = self.cipher.decrypt(twelve_data_key).decode()
            self.config["notify"]["wecom_webhook"] = self.cipher.decrypt(wecom_webhook).decode()
            self.config["notify"]["tg_token"] = self.cipher.decrypt(tg_token).decode()
            self.config["notify"]["tg_chat_id"] = self.cipher.decrypt(tg_chat_id).decode()

        except Exception as e:
            logger.error(f"Failed to decrypt credentials. Verify that ENCRYPTION_KEY is valid: {e}")
            raise

    @staticmethod
    async def _handle_health(_request):
        return web.Response(text="Bot is running", content_type='text/html')

    async def _run_services(self):
        await asyncio.gather(self.scan_engine.run())

    async def run_huggingface(self):
        # 1. 实例化 UI
        demo = self.scan_engine.ui_e.create_demo()

        # 2. 启动扫描引擎任务 (非阻塞)
        scan_task = asyncio.create_task(self.scan_engine.run())

        # 3. 使用 Gradio 6.0 推荐的启动方式
        logger.info("🚀 Starting Gradio Interface on port 7860...")

        # 4. launch 是一个阻塞操作，但在 asyncio 环境下
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            css=self.scan_engine.ui_e.theme_css,
            theme=gr.themes.Soft(),
            prevent_thread_lock=True
        )

        # 5. 让主协程等待扫描任务
        try:
            await scan_task
        except Exception as e:
            logger.error(f"扫描任务意外终止: {e}")

    async def run_local(self):
        logger.info("✅ Local Mode: Starting engines")
        await self._run_services()

    def start(self):
        try:
            if self.env_key:
                asyncio.run(self.run_huggingface())
            else:
                # asyncio.run(self.run_local())
                asyncio.run(self.run_huggingface())
        except KeyboardInterrupt:
            logger.warning("Stopped by user")
        except Exception as e:
            logger.error(f"Critical error: {e}")


# =====================================================
# 9. 信号通知、UI列表页
# =====================================================
class MsgUtils:

    extra_key_map = {
        "energy": "动能",
        "trend": "趋势",
        "squeeze_bars": "挤压",
        "bb_score": "分数",
        "changes": "走势",
        "changes_str": "涨幅",
        "sqz_status": "释放",
        "macd": "水平",
        "rsi_info": "强弱"
    }

    @staticmethod
    def build_row(res):
        # --- 1. 公共字段处理 ---
        strategy_name = res.get('strategy_name')
        symbol = res.get('symbol')
        interval = res.get('interval')
        date_str = res.get('date')
        time_str = res.get('time')
        price_str = res.get('price')
        price = float(res.get('price'))
        change = res.get('change')
        ema = float(res.get('ema'))
        rsi = float(res.get('rsi'))
        adx = float(res.get('adx'))
        adx_threshold = float(res.get('adx_threshold'))
        support = float(res.get('support'))
        resistance = float(res.get('resistance'))
        raw_signal = res.get('signal')
        atr = res.get('atr')
        parameters = json.dumps(res.get('parameters'), ensure_ascii=False)

        # --- 2. RSI判断 ---
        if rsi >= 70:
            i_b = "📈rsi"
        elif rsi <= 30:
            i_b = "📉rsi"
        else:
            i_b = "🗒️rsi"

        # --- 3. 信号判断 ---
        raw_sig = str(raw_signal).lower()
        if raw_sig == "long":
            signal_text = "🟢 long"
            r_b = "📈res" if price > resistance else "📉res"
        elif raw_sig == "short":
            signal_text = "🔴 short"
            r_b = "📈sup" if price > support else "📉sup"
        elif raw_sig == "watch_long":
            signal_text = "🟠 long"
            r_b = "📈res" if price > resistance else "📉res"
        elif raw_sig == "watch_short":
            signal_text = "🟠 short"
            r_b = "📈sup" if price > support else "📉sup"
        else:
            signal_text = "⚪"
            r_b = "📈sup" if price > support else "📉sup"

        e_b = "📈ema" if price > ema else "📉ema"
        a_b = "📈adx" if adx > adx_threshold else "📉adx"
        judge_text = f"{e_b} {r_b} {a_b} {i_b}"

        # --- 4. TradingView ---
        tv_symbol = symbol.upper().replace("/", "")
        groups = CONFIG.get("time").get("market_groups", {})
        forex_list = groups.get("forex_gold", [])
        stocks_list = groups.get("us_stocks", [])
        if any(k in tv_symbol for k in stocks_list):
            exchange = "NASDAQ"
        elif any(k in tv_symbol for k in forex_list):
            exchange = "FX"
        else:
            logger.error("没有配置对应的跳转链接")
            exchange = ""
        # 组装跳转链接
        tv_url = f"https://cn.tradingview.com/chart/?symbol={exchange}%3A{tv_symbol}"
        tv_link = f"[📊]({tv_url})"

        # --- 5. Extra 格式化逻辑 ---
        def _format_extra(data):
            parts = []
            for k, v in data.items():
                name = MsgUtils.extra_key_map.get(k, k)
                val_s = (str(v)
                         .replace("暗绿", "🟢")
                         .replace("亮绿", "🟢")
                         .replace("暗红", "🔴")
                         .replace("亮红", "🔴")
                         .replace("高", "⬆️")
                         .replace("低", "⬇️")
                         .replace("涨", "📈")
                         .replace("跌", "📉")
                         .replace("平", "🗒")
                         .replace("OFF", "⚪")
                         .replace("ON", "⚫"))
                val_s = re.sub(r"\[.*?]", "", val_s)
                parts.append(f"{name}: {val_s}")
            return " ".join(parts)

        format_extra = _format_extra(res.get('extra'))

        # --- 6. 返回行数据结构 ---
        return [
            strategy_name,    # 0策略
            interval,         # 1周期
            date_str,         # 2日期
            time_str[:5],     # 3时间
            symbol,           # 4代码
            tv_link,          # 5图表
            signal_text,      # 6信号
            price_str,        # 7现价
            f"{change}%",     # 8涨幅
            atr,              # 9止损
            judge_text,       # 10判断
            format_extra,     # 11其他
            parameters        # 12参数【一定放在最后一行】
        ]


if __name__ == "__main__":
    runner = RunEngine(CONFIG)
    runner.start()