#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import base64
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
from typing import Dict, Optional, Any, List
from cryptography.fernet import Fernet

CONFIG = {
    "watch_list": ["SUI", "DOGE"],

    "intervals": ["1H"],

    "api": {
        "active_exchange": "o",
        "o_base_url": "aHR0cHM6Ly93d3cub2t4LmNvbQ==",
        "b_base_url": "aHR0cHM6Ly9mYXBpLmJpbmFuY2UuY29t",
        "g_base_url": "aHR0cHM6Ly9hcGkuYml0Z2V0LmNvbQ==",
        "top_n": 10,
        "rank_by": "change",  # volume or change
        "min_volume": 500000,
        "max_concurrent": 8,
        "kline_limit": 1000,
        "exclude_tokens": ["BNB", "USDC", "TRX", "ADA", "OKB", "SOL", "XRP", "BCH", "LTC", "PUMP", "WLFI", "ICP", "ENA", "OP", "POL"]
    },

    "ui": {
        "ui_name": "huggingface",
        "refresh_interval": 5
    },

    "strategy": {
        "router": {
            "sqz": {
                "handler": "_run_sqz_strategy",
                "enabled": False,
                "desc": "sqz策略",
                "icon": "🎯"
            },
            "utb": {
                "handler": "_run_utb_strategy",
                "enabled": True,
                "desc": "utb策略",
                "icon": "🐮"
            },
            "rsi": {
                "handler": "_run_rsi_strategy",
                "enabled": False,
                "desc": "rsi策略",
                "icon": "🔥"
            }
        },

        "indicators": {

            "5M": {
                "stc_length": 80,
                "stc_fast_length": 27,
                "stc_slow_length": 50,
                "stc_factor": 0.5,

                "tma_fast_length": 5,
                "tma_slow_length": 8,
                "tma_vfactor": 0.618,

                "key_value": 2.0,
                "atr_period": 6,
                "use_ha": False,

                "bb_length": 20,
                "bb_mult": 1.8,
                "kc_length": 20,
                "kc_mult": 1.5,
                "use_true_range": True,
                "min_sqz_bars": 4,

                "ema_length": 200,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 25,

                "atr_length": 14,
                "atr_mult": 1.2,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            },

            "15M": {
                "stc_length": 80,
                "stc_fast_length": 27,
                "stc_slow_length": 50,
                "stc_factor": 0.5,

                "tma_fast_length": 5,
                "tma_slow_length": 8,
                "tma_vfactor": 0.618,

                "key_value": 2.0,
                "atr_period": 6,
                "use_ha": False,

                "bb_length": 20,
                "bb_mult": 1.8,
                "kc_length": 20,
                "kc_mult": 1.5,
                "use_true_range": True,
                "min_sqz_bars": 4,

                "ema_length": 200,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 25,

                "atr_length": 14,
                "atr_mult": 1.2,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            },

            "1H": {
                "stc_length": 80,
                "stc_fast_length": 27,
                "stc_slow_length": 50,
                "stc_factor": 0.5,

                "tma_fast_length": 5,
                "tma_slow_length": 8,
                "tma_vfactor": 0.618,

                "key_value": 3.0,
                "atr_period": 14,
                "use_ha": False,

                "bb_length": 20,
                "bb_mult": 1.8,
                "kc_length": 20,
                "kc_mult": 1.5,
                "use_true_range": True,
                "min_sqz_bars": 4,

                "ema_length": 200,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 25,

                "atr_length": 14,
                "atr_mult": 1.2,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            },

            "4H": {
                "stc_length": 80,
                "stc_fast_length": 27,
                "stc_slow_length": 50,
                "stc_factor": 0.5,

                "tma_fast_length": 5,
                "tma_slow_length": 8,
                "tma_vfactor": 0.618,

                "key_value": 2.0,
                "atr_period": 14,
                "use_ha": False,

                "bb_length": 20,
                "bb_mult": 1.8,
                "kc_length": 20,
                "kc_mult": 1.5,
                "use_true_range": True,
                "min_sqz_bars": 4,

                "ema_length": 200,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 25,

                "atr_length": 14,
                "atr_mult": 1.2,
                "atr_smooth": "RMA",

                "cm_fast_length": 12,
                "cm_slow_length": 26,
                "cm_signal_length": 9,

                "rsi_length": 14,
                "rsi_ma_length": 14,
                "rsi_smooth": "SMA"
            },

            "1D": {
                "stc_length": 80,
                "stc_fast_length": 27,
                "stc_slow_length": 50,
                "stc_factor": 0.5,

                "tma_fast_length": 5,
                "tma_slow_length": 8,
                "tma_vfactor": 0.618,

                "key_value": 2.0,
                "atr_period": 14,
                "use_ha": False,

                "bb_length": 20,
                "bb_mult": 1.8,
                "kc_length": 20,
                "kc_mult": 1.5,
                "use_true_range": True,
                "min_sqz_bars": 5,

                "ema_length": 200,

                "srb_left": 15,
                "srb_right": 15,

                "adx_length": 14,
                "adx_threshold": 20,

                "atr_length": 14,
                "atr_mult": 1.2,
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

    "notify": {
        "console_enable": True,
        "wecom_enable": True,
        "tg_enable": False,

        "wecom_webhook": None,
        "tg_token": None,
        "tg_chat_id": None
    }
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
pd.set_option('future.no_silent_downcasting', True)


class DataEngine:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.exchange = cfg.get("active_exchange").lower()
        self.o_base = base64.b64decode(cfg.get('o_base_url')).decode()
        self.b_base = base64.b64decode(cfg.get('b_base_url')).decode()
        self.g_base = base64.b64decode(cfg.get('g_base_url')).decode()

    async def get_active_symbols(self, session: aiohttp.ClientSession) -> List[str]:
        if self.exchange == "o":
            return await self._get_o_active_symbols(session)
        elif self.exchange == "b":
            return await self._get_b_active_symbols(session)
        elif self.exchange == "g":
            return await self._get_g_active_symbols(session)
        else:
            return await self._get_o_active_symbols(session)

    async def _get_b_active_symbols(self, session: aiohttp.ClientSession) -> List[str]:
        url = f"{self.b_base}/fapi/v1/ticker/24hr"
        try:
            async with session.get(url, timeout=10) as r:
                data = await r.json()
                if not isinstance(data, list):
                    logger.error(f"❌ [B] API error response: {data}")
                    return []

                df = pd.DataFrame(data)
                df['vol_usdt'] = pd.to_numeric(df['quoteVolume'], errors='coerce')
                df['change_pct'] = pd.to_numeric(df['priceChangePercent'], errors='coerce')
                df = df[df['symbol'].str.endswith('USDT')]

                exclude = self.cfg.get('exclude_tokens', [])
                for token in exclude:
                    df = df[~df['symbol'].str.contains(token, regex=False)]

                rank_strategy = self.cfg.get('rank_by', 'volume')
                if rank_strategy == 'change':
                    df = df.sort_values('change_pct', ascending=False)
                    logger.info("📊 [B] Sorting strategy: 24h price change")
                else:
                    df = df.sort_values('vol_usdt', ascending=False)
                    logger.info("📊 [B] Sorting strategy: 24h trading volume")

                top_n = self.cfg.get('top_n', 50)
                symbols = df.head(top_n)['symbol'].tolist()
                logger.info(f"🔝 [B] Top 5: {symbols[:5]}")
                return symbols

        except Exception as e:
            logger.error(f"❌ [B] Failed to get trading pair: {e}")
            return []

    async def _get_g_active_symbols(self, session: aiohttp.ClientSession) -> List[str]:
        url = f"{self.g_base}/api/v2/mix/market/tickers"
        params = {"productType": "USDT-FUTURES"}
        try:
            async with session.get(url, params=params, timeout=10) as r:
                res = await r.json()
                data = res.get('data', [])
                if not data:
                    logger.error("❌ [G] No data returned")
                    return []

                df = pd.DataFrame(data)

                df['vol_usdt'] = pd.to_numeric(df['usdtVolume'], errors='coerce')

                df['change_pct'] = pd.to_numeric(df['change24h'], errors='coerce')

                df = df[df['symbol'].str.endswith('USDT')]

                if df.empty:
                    logger.error("❌ [G] Data is empty after filtering usdt contracts")
                    return []

                exclude = self.cfg.get('exclude_tokens', [])
                for token in exclude:
                    df = df[~df['symbol'].str.contains(token, regex=False)]

                rank_strategy = self.cfg.get('rank_by', 'volume')
                if rank_strategy == 'change':
                    df = df.sort_values('change_pct', ascending=False)
                    logger.info("📊 [G] Sorting strategy: 24h price change")
                else:
                    df = df.sort_values('vol_usdt', ascending=False)
                    logger.info("📊 [G] Sorting strategy: 24h trading volume")

                top_n = self.cfg.get('top_n', 50)
                symbols = df.head(top_n)['symbol'].tolist()

                for core in ["BTCUSDT", "ETHUSDT"]:
                    if core not in symbols:
                        symbols.insert(0, core)

                logger.info(f"🔝 [G] Top 5: {symbols[:5]}")
                return symbols[:top_n]

        except Exception as e:
            logger.error(f"❌ [G] Failed to get trading pair: {e}")
            return []

    async def _get_o_active_symbols(self, session: aiohttp.ClientSession) -> List[str]:
        url = f"{self.o_base}/api/v5/market/tickers"
        params = {"instType": "SWAP"}
        try:
            async with session.get(url, params=params, timeout=10) as r:
                res = await r.json()
                data = res.get('data', [])
                if not data:
                    return []

                df = pd.DataFrame(data)
                last_price = pd.to_numeric(df['last'], errors='coerce')
                open_24h = pd.to_numeric(df['open24h'], errors='coerce')
                df['vol_usdt'] = pd.to_numeric(df['volCcy24h'], errors='coerce') * last_price
                df['change_pct'] = (last_price - open_24h) / open_24h
                df = df[df['instId'].str.endswith('-USDT-SWAP')]

                exclude = self.cfg.get('exclude_tokens', [])
                for token in exclude:
                    df = df[~df['instId'].str.contains(token, regex=False)]

                rank_strategy = self.cfg.get('rank_by', 'volume')
                if rank_strategy == 'change':
                    df = df.sort_values('change_pct', ascending=False)
                    logger.info("📊 [O] Sorting strategy: 24h price change")
                else:
                    df = df.sort_values('vol_usdt', ascending=False)
                    logger.info("📊 [O] Sorting strategy: 24h trading volume")

                top_n = self.cfg.get('top_n', 50)
                symbols = df.head(top_n)['instId'].tolist()

                for core in ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]:
                    if core not in symbols:
                        symbols.insert(0, core)

                logger.info(f"🔝 [O] Top 5: {symbols[:5]}")
                return symbols[:top_n]

        except Exception as e:
            logger.error(f"❌ [O] Failed to get trading pair: {e}")
            return []

    def format_symbol(self, token: str) -> str:
        clean_token = token.upper().replace("-USDT-SWAP", "").replace("USDT", "")
        if self.exchange == "o":
            return f"{clean_token}-USDT-SWAP"
        else:
            return f"{clean_token}USDT"

    async def fetch_klines(self, session: aiohttp.ClientSession, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        if self.exchange == "o":
            return await self._fetch_o_klines(session, symbol, interval)
        elif self.exchange == "b":
            return await self._fetch_b_klines(session, symbol, interval)
        else:
            return await self._fetch_g_klines(session, symbol, interval)

    async def _fetch_g_klines(self, session: aiohttp.ClientSession, symbol: str, interval: str) -> Optional[
        pd.DataFrame]:
        url = f"{self.g_base}/api/v2/mix/market/candles"
        bg_interval = interval.lower().replace('d', 'day')
        params = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "granularity": bg_interval,
            "limit": self.cfg.get('kline_limit', 1000)
        }
        try:
            async with session.get(url, params=params, timeout=10) as r:
                res = await r.json()
                data = res.get('data', [])
                if not data:
                    return None

                df = pd.DataFrame(data).iloc[::-1].reset_index(drop=True)
                df = df[[0, 1, 2, 3, 4, 5]].astype(float)
                df.columns = ['ts', 'open', 'high', 'low', 'close', 'volume']
                df['date'] = pd.to_datetime(df['ts'], unit='ms') + timedelta(hours=8)
                df.set_index('date', inplace=True)
                return df
        except Exception as e:
            logger.error(f"❌ [G] Failed to get K-line ({symbol}): {e}")
            return None

    async def _fetch_o_klines(self, session: aiohttp.ClientSession, symbol: str, interval: str) -> Optional[
        pd.DataFrame]:
        url = f"{self.o_base}/api/v5/market/candles"
        o_interval = interval.lower() if interval.upper().endswith('M') else interval.upper()
        params = {
            "instId": symbol,
            "bar": o_interval,
            "limit": self.cfg.get('kline_limit', 1000)
        }
        try:
            async with session.get(url, params=params, timeout=10) as r:
                res = await r.json()
                data = res.get('data', [])
                if not data:
                    return None

                df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'volCcy', 'volCcyQuote', 'confirm'])
                df = df.iloc[::-1].reset_index(drop=True)
                df = df[df['confirm'] == '1'].copy()
                df = df[['ts', 'o', 'h', 'l', 'c', 'v']].astype(float)
                df.columns = ['ts', 'open', 'high', 'low', 'close', 'volume']
                df['date'] = pd.to_datetime(df['ts'], unit='ms') + timedelta(hours=8)
                df.set_index('date', inplace=True)
                return df
        except Exception as e:
            logger.error(f"❌ [O] Failed to get K-line ({symbol}): {e}")
            return None

    async def _fetch_b_klines(self, session: aiohttp.ClientSession, symbol: str, interval: str) -> Optional[
        pd.DataFrame]:
        url = f"{self.b_base}/fapi/v1/klines"
        b_interval = interval.lower()
        params = {
            "symbol": symbol,
            "interval": b_interval,
            "limit": self.cfg.get('kline_limit', 1000)
        }
        try:
            async with session.get(url, params=params, timeout=10) as r:
                data = await r.json()
                if isinstance(data, dict) or not data:
                    return None

                df = pd.DataFrame(data).iloc[:-1]
                df = df[[0, 1, 2, 3, 4, 5]].astype(float)
                df.columns = ['ts', 'open', 'high', 'low', 'close', 'volume']
                df['date'] = pd.to_datetime(df['ts'], unit='ms') + timedelta(hours=8)
                df.set_index('date', inplace=True)
                return df
        except Exception as e:
            logger.error(f"❌ [B] Failed to get K-line ({symbol}): {e}")
            return None


class IndicatorEngine:
    def __init__(self, st_cfg: dict):
        self.cfg = st_cfg

    @staticmethod
    def tv_linreg(series: pd.Series, length: int):
        if pd.isna(series).any() or len(series) < length:
            return np.nan
        x = np.arange(length)
        y_vals = series.values[-length:]
        a = np.vstack([x, np.ones(length)]).T
        try:
            m, b = np.linalg.lstsq(a, y_vals, rcond=None)[0]
            return m * (length - 1) + b
        except Exception as e:
            logger.error(f"❌ Linear regression fit failed: {e}")
            return np.nan

    @staticmethod
    def true_range(df: pd.DataFrame) -> pd.Series:
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    @staticmethod
    def add_squeeze_counter(df: pd.DataFrame) -> pd.DataFrame:
        counter = 0
        current_state = None
        sqz_id_list = []
        for status in df["sqz_status"]:
            if status in ["on", "off"]:
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
        if pd.isna(val) or pd.isna(val_prev):
            return "undefined"
        if val > 0:
            return "lime" if val > val_prev else "green"
        elif val < 0:
            return "red" if val < val_prev else "maroon"
        else:
            return "neutral"

    @staticmethod
    def add_color_counter(df: pd.DataFrame) -> pd.DataFrame:
        counter = 0
        current_color = None
        sqz_hcolor_id_list = []
        skip_colors = {'undefined', 'neutral'}

        for color in df["sqz_hcolor"]:
            if color in skip_colors:
                current_color = None
                counter = 0
                sqz_hcolor_id_list.append(0)
            else:
                if color == current_color:
                    counter += 1
                else:
                    current_color = color
                    counter = 1
                sqz_hcolor_id_list.append(counter)

        df["sqz_hcolor_id"] = sqz_hcolor_id_list

        return df

    def squeeze_momentum_indicator(self, df: pd.DataFrame, bb_length: int = 20, bb_mult: float = 1.2,
                                   kc_length: int = 20, kc_mult: float = 1.2,
                                   use_true_range: bool = True) -> pd.DataFrame:
        close, high, low = df['close'], df['high'], df['low']

        basis = close.rolling(bb_length).mean()
        dev = bb_mult * close.rolling(bb_length).std(ddof=0)
        upper_bb, lower_bb = basis + dev, basis - dev

        ma = close.rolling(kc_length).mean()
        r = self.true_range(df) if use_true_range else (high - low)
        rangema = r.rolling(kc_length).mean()
        upper_kc, lower_kc = ma + rangema * kc_mult, ma - rangema * kc_mult

        sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
        sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)
        df["sqz_status"] = np.select([sqz_on, sqz_off], ["on", "off"], default="no")

        highest_h = high.rolling(kc_length).max()
        lowest_l = low.rolling(kc_length).min()
        avg_hl = (highest_h + lowest_l) / 2
        sma_close = close.rolling(kc_length).mean()
        mid = (avg_hl + sma_close) / 2
        source_mid = close - mid

        histogram_value = source_mid.rolling(kc_length).apply(lambda x: self.tv_linreg(pd.Series(x), kc_length),
                                                              raw=False)

        df["sqz_hvalue"] = histogram_value

        df["sqz_pre_hvalue"] = histogram_value.shift(1)

        df = self.add_squeeze_counter(df)

        df["sqz_hcolor"] = df.apply(
            lambda res: self.get_squeeze_momentum_histogram_color(res["sqz_hvalue"], res["sqz_pre_hvalue"]), axis=1)

        df.drop(columns=["sqz_pre_hvalue"], inplace=True)

        df = self.add_color_counter(df)

        return df

    @staticmethod
    def ema_indicator(df: pd.DataFrame, ema_length: int = 200) -> pd.DataFrame:
        df["ema"] = df['close'].ewm(span=ema_length, adjust=False).mean()

        return df

    @staticmethod
    def support_resistance_indicator(df: pd.DataFrame, srb_left: int = 15, srb_right: int = 15) -> pd.DataFrame:
        window = srb_left + srb_right + 1

        def is_pivot_high(x):
            mid_val = x[srb_left]
            left = x[:srb_left]
            right = x[srb_left + 1:]
            if np.all(mid_val >= left) and np.all(mid_val > right):
                return mid_val
            return np.nan

        def is_pivot_low(x):
            mid_val = x[srb_left]
            left = x[:srb_left]
            right = x[srb_left + 1:]
            if np.all(mid_val <= left) and np.all(mid_val < right):
                return mid_val
            return np.nan

        raw_res = df['high'].rolling(window).apply(is_pivot_high, raw=True)
        raw_sup = df['low'].rolling(window).apply(is_pivot_low, raw=True)

        df['srb_res'] = raw_res.ffill()
        df['srb_sup'] = raw_sup.ffill()

        pivot_high_pos = raw_res.notna().shift(-srb_right).fillna(False).astype(bool)
        pivot_low_pos = raw_sup.notna().shift(-srb_right).fillna(False).astype(bool)

        df['srb_lab'] = 'no'
        df.loc[pivot_low_pos, 'srb_lab'] = 'sup'
        df.loc[pivot_high_pos, 'srb_lab'] = 'res'

        return df

    @staticmethod
    def wilder_smoothing(series: pd.Series, length: int):
        values = series.values
        smoothed = np.empty_like(values)
        smoothed.fill(np.nan)

        smoothed[length - 1] = np.sum(values[:length])

        for i in range(length, len(values)):
            smoothed[i] = smoothed[i - 1] - (smoothed[i - 1] / length) + values[i]

        return pd.Series(smoothed, index=series.index)

    def adx_di_indicator(self, df: pd.DataFrame, adx_length: int = 14, adx_threshold: int = 25) -> pd.DataFrame:
        high_low = df['high'] - df['low']
        high_prev_close = np.abs(df['high'] - df['close'].shift(1))
        low_prev_close = np.abs(df['low'] - df['close'].shift(1))

        df['true_range'] = high_low.combine(high_prev_close, max).combine(low_prev_close, max)

        up_move = df['high'] - df['high'].shift(1)
        down_move = df['low'].shift(1) - df['low']

        df['adx_plus'] = np.where((up_move > down_move) & (up_move > 0), up_move, 0)

        df['adx_minus'] = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        df['smoothed_tr'] = self.wilder_smoothing(df['true_range'], adx_length)
        df['smoothed_dm_plus'] = self.wilder_smoothing(df['adx_plus'], adx_length)
        df['smoothed_dm_minus'] = self.wilder_smoothing(df['adx_minus'], adx_length)

        df['adx_plus'] = (df['smoothed_dm_plus'] / df['smoothed_tr']) * 100
        df['adx_minus'] = (df['smoothed_dm_minus'] / df['smoothed_tr']) * 100

        sum_di = df['adx_plus'] + df['adx_minus']
        df['dx'] = np.where(sum_di != 0, np.abs(df['adx_plus'] - df['adx_minus']) / sum_di * 100, 0)

        df['adx'] = df['dx'].rolling(window=adx_length).mean()
        df['adx_threshold'] = adx_threshold

        df.drop(columns=['true_range', 'smoothed_tr', 'smoothed_dm_plus', 'smoothed_dm_minus', 'dx'], inplace=True)

        return df

    @staticmethod
    def bollinger_indicator(df: pd.DataFrame, bb_length: int = 12, bb_mult: float = 1.8) -> pd.DataFrame:
        df['bb_basis'] = df['close'].rolling(window=bb_length).mean()

        df['bb_std'] = df['close'].rolling(window=bb_length).std()

        df['bb_upper'] = df['bb_basis'] + (bb_mult * df['bb_std'])
        df['bb_lower'] = df['bb_basis'] - (bb_mult * df['bb_std'])

        df['bb_bw'] = (df['bb_upper'] - df['bb_lower']) / df['bb_basis']

        df['bb_bw_rank'] = df['bb_bw'].rank(pct=True, ascending=False) * 100

        return df

    @staticmethod
    def ma_smoothing(series: pd.Series, length: int, method: str) -> pd.Series:
        method = method.upper()

        if method == "SMA":
            return series.rolling(length).mean()

        if method == "EMA":
            return series.ewm(span=length, adjust=False).mean()

        if method == "RMA":
            rma = np.full(len(series), np.nan)

            if len(series) < length:
                return pd.Series(rma, index=series.index)

            rma[length - 1] = series.iloc[:length].mean()

            alpha = 1 / length
            for i in range(length, len(series)):
                rma[i] = alpha * series.iloc[i] + (1 - alpha) * rma[i - 1]

            return pd.Series(rma, index=series.index)

        if method == "WMA":
            weights = np.arange(1, length + 1)

            return series.rolling(length).apply(
                lambda x: np.dot(x, weights) / weights.sum(),
                raw=True,
            )

        raise ValueError(f"❌ Unknown smoothing method: {method}")

    def atr_indicator(self, df: pd.DataFrame, atr_length: int = 14, atr_mult: float = 1.0,
                      atr_smooth: str = "RMA") -> pd.DataFrame:
        tr = self.true_range(df)

        atr = self.ma_smoothing(tr, atr_length, atr_smooth)

        df["atr"] = atr
        df["atr_mult"] = atr * atr_mult

        df["atr_short_stop"] = df["high"] + df["atr_mult"]

        df["atr_long_stop"] = df["low"] - df["atr_mult"]

        return df

    @staticmethod
    def cm_macd_ult_indicator(df: pd.DataFrame, cm_fast_length: int = 12, cm_slow_length: int = 26,
                              cm_signal_length: int = 9) -> pd.DataFrame:
        fast_ma = df["close"].ewm(span=cm_fast_length, adjust=False).mean()
        slow_ma = df["close"].ewm(span=cm_slow_length, adjust=False).mean()

        df["cm_macd"] = fast_ma - slow_ma

        df["cm_signal"] = df["cm_macd"].rolling(window=cm_signal_length).mean()
        df["cm_hist"] = df["cm_macd"] - df["cm_signal"]

        df["cm_hist_prev"] = df["cm_hist"].shift(1)

        conditions = [
            (df["cm_hist"] > 0) & (df["cm_hist"] > df["cm_hist_prev"]),
            (df["cm_hist"] > 0) & (df["cm_hist"] <= df["cm_hist_prev"]),
            (df["cm_hist"] <= 0) & (df["cm_hist"] < df["cm_hist_prev"]),
            (df["cm_hist"] <= 0) & (df["cm_hist"] >= df["cm_hist_prev"])
        ]
        choices = ["aqua", "blue", "red", "maroon"]
        df["cm_hist_color"] = np.select(conditions, choices, default="gray")

        df["cm_prev_macd"] = df["cm_macd"].shift(1)
        df["cm_prev_signal"] = df["cm_signal"].shift(1)

        df["cm_cross_point"] = 0
        df.loc[(df["cm_prev_macd"] < df["cm_prev_signal"]) & (df["cm_macd"] >= df["cm_signal"]), "cm_cross_point"] = 1
        df.loc[(df["cm_prev_macd"] > df["cm_prev_signal"]) & (df["cm_macd"] <= df["cm_signal"]), "cm_cross_point"] = -1

        df["cm_cross_status"] = df["cm_cross_point"].replace(0, np.nan).ffill()
        df["cm_cross_status"] = df["cm_cross_status"].fillna(0).astype(int)

        if df["cm_cross_status"].isna().any():
            initial_status = np.where(df["cm_macd"] >= df["cm_signal"], 1, -1)
            df["cm_cross_status"] = df["cm_cross_status"].fillna(pd.Series(initial_status, index=df.index))

        df.drop(columns=["cm_hist_prev", "cm_prev_macd", "cm_prev_signal"], inplace=True)

        return df

    @staticmethod
    def rsi_indicator(df: pd.DataFrame, rsi_length: int = 14, rsi_ma_length: int = 14,
                      rsi_smooth: str = "SMA") -> pd.DataFrame:
        change = df['close'].diff()

        gain = change.clip(lower=0)
        loss = -change.clip(upper=0)

        alpha = 1 / rsi_length
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

        rsi = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
        df["rsi"] = np.where(avg_loss == 0, 100, np.where(avg_gain == 0, 0, rsi))

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

    @staticmethod
    def utb_indicator(df: pd.DataFrame, key_value: float = 2.0, atr_period: int = 14,
                      use_ha: bool = False) -> pd.DataFrame:

        if use_ha:
            ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4

            ha_open = np.zeros(len(df))
            ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
            for i in range(1, len(df)):
                ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2

            src = ha_close
        else:
            src = df['close']

        close = df['close']
        high = df['high']
        low = df['low']

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)

        atr = tr.ewm(alpha=1.0 / atr_period, min_periods=atr_period, adjust=False).mean()
        n_loss = key_value * atr

        src_arr = src.to_numpy()
        nloss_arr = n_loss.to_numpy()
        stop_arr = np.zeros(len(df))

        for i in range(len(df)):
            if i == 0 or np.isnan(nloss_arr[i]):
                stop_arr[i] = src_arr[i]
                continue

            c, pc, ps, nl = src_arr[i], src_arr[i - 1], stop_arr[i - 1], nloss_arr[i]

            if c > ps and pc > ps:
                stop_arr[i] = max(ps, c - nl)
            elif c < ps and pc < ps:
                stop_arr[i] = min(ps, c + nl)
            elif c > ps:
                stop_arr[i] = c - nl
            else:
                stop_arr[i] = c + nl

        utb_stop = pd.Series(stop_arr, index=df.index, name='utb_stop')

        pos_arr = np.zeros(len(df), dtype=int)

        for i in range(1, len(df)):
            c_prev = src_arr[i - 1]
            c_cur = src_arr[i]
            s_prev = stop_arr[i - 1]

            if c_prev < s_prev < c_cur:
                pos_arr[i] = 1
            elif c_prev > s_prev > c_cur:
                pos_arr[i] = -1
            else:
                pos_arr[i] = pos_arr[i - 1]

        src_series = pd.Series(src_arr, index=df.index)
        above = (src_series > utb_stop) & (src_series.shift(1) <= utb_stop.shift(1))
        below = (utb_stop > src_series) & (utb_stop.shift(1) <= src_series.shift(1))

        utb_buy = (src_series > utb_stop) & above
        utb_sell = (src_series < utb_stop) & below

        ut_signal = pd.Series('no', index=df.index, name='utb_signal')
        ut_signal = ut_signal.mask(utb_buy, 'buy')
        utb_signal = ut_signal.mask(utb_sell, 'sell')

        utb_trend = pd.Series(
            np.where(
                pos_arr == 1, 'bull',
                np.where(
                    pos_arr == -1, 'bear',
                    np.where(src_arr > stop_arr, 'bull', 'bear')
                )
            ),
            index=df.index,
            name='utb_trend',
        )

        df['utb_signal'] = utb_signal
        df['utb_trend'] = utb_trend

        return df

    @staticmethod
    def stc_indicator(df: pd.DataFrame, stc_length: int = 12, stc_fast_length: int = 26, stc_slow_length: int = 50,
                      stc_factor: float = 0.5) -> pd.DataFrame:
        src = df['close'].values
        n = len(src)

        def get_pine_ema(dat: np.ndarray, length: int) -> np.ndarray:
            alpha = 2.0 / (length + 1)
            ema_arr = np.full(n, np.nan)
            current_ema = np.nan
            for x in range(n):
                val = dat[x]
                if np.isnan(val):
                    continue
                if np.isnan(current_ema):
                    current_ema = val
                else:
                    current_ema = alpha * val + (1 - alpha) * current_ema
                ema_arr[x] = current_ema
            return ema_arr

        def rolling_lowest(dat: np.ndarray, length: int) -> np.ndarray:
            result = np.full(n, np.nan)
            for x in range(n):
                start = max(0, x - length + 1)
                window = dat[start: x + 1]
                valid = window[~np.isnan(window)]
                if len(valid) > 0:
                    result[x] = np.min(valid)
            return result

        def rolling_highest(dat: np.ndarray, length: int) -> np.ndarray:
            result = np.full(n, np.nan)
            for x in range(n):
                start = max(0, x - length + 1)
                window = dat[start: x + 1]
                valid = window[~np.isnan(window)]
                if len(valid) > 0:
                    result[x] = np.max(valid)
            return result

        fast_ma = get_pine_ema(src, stc_fast_length)
        slow_ma = get_pine_ema(src, stc_slow_length)
        macd = fast_ma - slow_ma

        macd_lowest = rolling_lowest(macd, stc_length)
        macd_highest = rolling_highest(macd, stc_length)

        f1 = np.full(n, np.nan)
        d1 = np.zeros(n)

        for i in range(n):
            macd_range = macd_highest[i] - macd_lowest[i]
            if not np.isnan(macd_range) and macd_range > 0:
                f1[i] = (macd[i] - macd_lowest[i]) / macd_range * 100
            else:
                f1[i] = f1[i - 1] if i > 0 and not np.isnan(f1[i - 1]) else 0.0

            d1[i] = d1[i - 1] + stc_factor * (f1[i] - d1[i - 1]) if i > 0 else f1[i]

        d1_lowest = rolling_lowest(d1, stc_length)
        d1_highest = rolling_highest(d1, stc_length)

        f2 = np.full(n, np.nan)
        stc = np.zeros(n)

        for i in range(n):
            d1_range = d1_highest[i] - d1_lowest[i]
            if not np.isnan(d1_range) and d1_range > 0:
                f2[i] = (d1[i] - d1_lowest[i]) / d1_range * 100
            else:
                f2[i] = f2[i - 1] if i > 0 and not np.isnan(f2[i - 1]) else 0.0

            stc[i] = stc[i - 1] + stc_factor * (f2[i] - stc[i - 1]) if i > 0 else f2[i]

        trends = ["bear"] * n

        for i in range(1, n):
            if np.isnan(stc[i]) or np.isnan(stc[i - 1]):
                trends[i] = trends[i - 1]
            elif stc[i] > stc[i - 1]:
                trends[i] = "bull"
            else:
                trends[i] = "bear"

        signals = ["no"] * n

        for i in range(1, n):
            if trends[i] == "bull" and trends[i - 1] == "bear":
                signals[i] = "buy"
            elif trends[i] == "bear" and trends[i - 1] == "bull":
                signals[i] = "sell"

        df['stc'] = np.round(stc.astype(float), 4)
        df['stc_signal'] = signals
        df['stc_trend'] = trends

        pd.options.display.float_format = '{:.4f}'.format

        return df

    @staticmethod
    def tma_indicator(df: pd.DataFrame, tma_fast_length: int = 5, tma_slow_length: int = 8,
                      tma_vfactor: float = 0.618) -> pd.DataFrame:

        def _gd(series, length, vol_factor):
            ema1 = series.ewm(span=length, adjust=False).mean()
            ema2 = ema1.ewm(span=length, adjust=False).mean()
            return ema1 * (1 + vol_factor) - ema2 * vol_factor

        def _t3(series, length, vol_factor):
            gd1 = _gd(series, length, vol_factor)
            gd2 = _gd(gd1, length, vol_factor)
            gd3 = _gd(gd2, length, vol_factor)
            return gd3

        df['t3_fast'] = _t3(df['close'], tma_fast_length, tma_vfactor)
        df['t3_slow'] = _t3(df['close'], tma_slow_length, tma_vfactor)

        df['t3_signal'] = "no"

        cross_up = (df['t3_fast'] > df['t3_slow']) & (df['t3_fast'].shift(1) <= df['t3_slow'].shift(1))
        cross_down = (df['t3_fast'] < df['t3_slow']) & (df['t3_fast'].shift(1) >= df['t3_slow'].shift(1))

        df.loc[cross_up, 't3_signal'] = "buy"
        df.loc[cross_down, 't3_signal'] = "sell"

        df['t3_trend'] = np.where(df['t3_fast'] > df['t3_slow'], "bull", "bear")

        return df

    def calculate(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        df = df.copy()

        cfg_group = self.cfg.get("indicators", {})
        if interval.upper() not in cfg_group:
            raise ValueError(f"❌ Invalid interval [{interval}] not found in indicators config")

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

        key_value = float(indicators_params["key_value"])
        atr_period = int(indicators_params["atr_period"])
        use_ha = indicators_params["use_ha"]

        stc_length = int(indicators_params["stc_length"])
        stc_fast_length = int(indicators_params["stc_fast_length"])
        stc_slow_length = int(indicators_params["stc_slow_length"])
        stc_factor = float(indicators_params["stc_factor"])

        tma_fast_length = int(indicators_params["tma_fast_length"])
        tma_slow_length = int(indicators_params["tma_slow_length"])
        tma_vfactor = float(indicators_params["tma_vfactor"])

        df = self.squeeze_momentum_indicator(
            df,
            bb_length=bb_length,
            bb_mult=bb_mult,
            kc_length=kc_length,
            kc_mult=kc_mult,
            use_true_range=use_true_range
        )

        df = self.ema_indicator(
            df,
            ema_length=ema_length
        )

        df = self.support_resistance_indicator(
            df,
            srb_left=srb_left,
            srb_right=srb_right
        )

        df = self.adx_di_indicator(
            df,
            adx_length=adx_length,
            adx_threshold=adx_threshold
        )

        df = self.atr_indicator(
            df,
            atr_length=atr_length,
            atr_mult=atr_mult,
            atr_smooth=atr_smooth
        )

        df = self.cm_macd_ult_indicator(
            df,
            cm_fast_length=cm_fast_length,
            cm_slow_length=cm_slow_length,
            cm_signal_length=cm_signal_length
        )

        df = self.rsi_indicator(
            df,
            rsi_length=rsi_length,
            rsi_ma_length=rsi_ma_length,
            rsi_smooth=rsi_smooth
        )

        df = self.bollinger_indicator(
            df,
            bb_length=bb_length,
            bb_mult=bb_mult
        )

        df['change'] = df['close'].ffill().pct_change()

        df = self.utb_indicator(
            df,
            key_value=key_value,
            atr_period=atr_period,
            use_ha=use_ha
        )

        df = self.stc_indicator(
            df,
            stc_length=stc_length,
            stc_fast_length=stc_fast_length,
            stc_slow_length=stc_slow_length,
            stc_factor=stc_factor
        )

        df = self.tma_indicator(
            df,
            tma_fast_length=tma_fast_length,
            tma_slow_length=tma_slow_length,
            tma_vfactor=tma_vfactor
        )

        return df


class StrategyEngine:
    def __init__(self, st_cfg: dict):
        self.cfg = st_cfg
        self._cached_params = {}

        self.strategy_router = {}
        self._init_strategy_router()

    def _init_strategy_router(self):
        router_cfg = self.cfg.get("router")

        for strategy_id, info in router_cfg.items():
            if info.get("enabled"):
                handler_name = info.get("handler")
                method = getattr(self, handler_name, None)
                if method:
                    self.strategy_router[strategy_id] = method
                else:
                    logger.error(f"❌ Strategy {strategy_id} is configured but handler {handler_name} was not found")

    def _get_strategy_params(self, interval: str) -> dict:
        interval_key = interval.upper()

        if interval_key in self._cached_params:
            return self._cached_params[interval_key]

        p = self.cfg.get("indicators", {}).get(interval_key)
        if not p:
            raise ValueError(
                f"❌ Configuration for interval {interval_key} is missing. Please check the configuration file.")

        params = {
            "stc_length": int(p.get("stc_length")),
            "stc_fast_length": int(p.get("stc_fast_length")),
            "stc_slow_length": int(p.get("stc_slow_length")),
            "stc_factor": float(p.get("stc_factor")),

            "tma_fast_length": int(p.get("tma_fast_length")),
            "tma_slow_length": int(p.get("tma_slow_length")),
            "tma_vfactor": float(p.get("tma_vfactor")),

            "key_value": float(p.get("key_value")),
            "atr_period": int(p.get("atr_period")),
            "use_ha": int(p.get("use_ha")),

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

    def get_sequence_values(self, df: pd.DataFrame, srb_lab: str):
        col = f'srb_{srb_lab}'

        history = df[df['srb_lab'] == srb_lab].tail(4)

        latest_row = df.iloc[[-1]]

        srb_df = pd.concat([history, latest_row])
        srb_df = srb_df[~srb_df[col].duplicated(keep='first')]

        values = srb_df[col].tolist()

        price_sequence = '-'.join(str(self.format_price(v)) for v in values)

        trends = []
        pcts = []
        for i in range(1, len(values)):
            direction = '高' if values[i] >= values[i - 1] else '低'
            pct = abs(values[i] / values[i - 1] - 1) * 100
            trends.append(direction)
            pcts.append(f'{pct:.1f}%')

        trend_sequence = ''.join(trends)
        pct_sequence = '-'.join(pcts)

        return price_sequence, trend_sequence, pct_sequence

    @staticmethod
    def get_anchor_stats(df: pd.DataFrame, srb_lab: str):
        signal_loc = len(df) - 1

        anchor_df = df[df['srb_lab'] == srb_lab]
        if len(anchor_df) == 0:
            return None, None

        anchor_idx = anchor_df.index[-1]
        anchor_loc = df.index.get_loc(anchor_idx)
        bars_since_anchor = str(signal_loc - anchor_loc)

        segment = df.iloc[anchor_loc: signal_loc + 1]

        if srb_lab == 'res':
            anchor_price = df.iloc[-1]['srb_res']
            extreme = segment['low'].min()
            range_pct = f"{abs((anchor_price - extreme) / extreme) * 100:.2f}%"
        else:
            anchor_price = df.iloc[-1]['srb_sup']
            extreme = segment['high'].max()
            range_pct = f"{abs((extreme - anchor_price) / anchor_price) * 100:.2f}%"

        return bars_since_anchor, range_pct

    @staticmethod
    def get_bb_squeeze_score(df: pd.DataFrame, squeeze_count: int) -> str:
        segment = df.iloc[-(squeeze_count + 1): -1]

        if segment['bb_bw_rank'].dropna().empty:
            return "empty"

        n_score = segment['bb_bw_rank'].mean()

        basis_seg = segment['bb_basis']

        price_range_ratio = (basis_seg.max() - basis_seg.min()) / basis_seg.mean()

        h_score = max(0, min(100, 100 * (1 - (price_range_ratio / 0.005))))

        return f"n {n_score:02.0f} | s {h_score:02.0f} | d {price_range_ratio * 100:.2f}%"

    @staticmethod
    def get_count_consecutive(df: pd.DataFrame, srb_lab: str):
        count = 0
        for i in range(len(df) - 1, -1, -1):
            row = df.iloc[i]
            if row['sqz_status'] == 'off' and row['sqz_hcolor'] == 'lime' if srb_lab == 'res' else 'red':
                count += 1
            else:
                break
        return count

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

    def _run_sqz_strategy(self, df: pd.DataFrame, strategy_params: dict) -> Dict[str, Any]:
        min_sqz_bars = strategy_params['min_sqz_bars']

        cur_row = df.iloc[-1]
        pre_row = df.iloc[-2]

        srb_res = cur_row['srb_res']
        srb_sup = cur_row['srb_sup']

        cur_close = cur_row['close']
        pre_close = pre_row['close']

        pre_sqz_status = pre_row['sqz_status']
        cur_sqz_status = cur_row['sqz_status']
        cur_sqz_hcolor = cur_row['sqz_hcolor']
        pre_sqz_id = pre_row['sqz_id']

        buy_cond_1 = (
            cur_sqz_hcolor == 'lime'
            and cur_sqz_status == 'off'
            and pre_sqz_status == 'on'
            and pre_sqz_id >= min_sqz_bars
        )

        consecutive_off_lime = self.get_count_consecutive(df.tail(20), 'res')
        off_lime_start_idx = len(df) - consecutive_off_lime - 1
        pre_off_lime_row = df.iloc[off_lime_start_idx] if off_lime_start_idx >= 0 else None

        buy_cond_2 = (
            pre_close < srb_res
            and cur_sqz_status == 'off'
            and cur_sqz_hcolor == 'lime'
            and consecutive_off_lime <= 1
            and pre_off_lime_row is not None
            and pre_off_lime_row['sqz_status'] == 'on'
            and pre_off_lime_row['sqz_id'] >= min_sqz_bars
        )

        close_t4 = df.iloc[-5]['close']
        close_t5 = df.iloc[-6]['close']
        close_t6 = df.iloc[-7]['close']
        up_res_count = sum([close_t4 > srb_res, close_t5 > srb_res, close_t6 > srb_res])

        if buy_cond_1 and up_res_count == 0:
            buy_release = '压力释放'
        elif buy_cond_2:
            buy_release = '已过亮绿'
        else:
            buy_release = None

        sell_cond_1 = (
            cur_sqz_hcolor == 'red'
            and cur_sqz_status == 'off'
            and pre_sqz_status == 'on'
            and pre_sqz_id >= min_sqz_bars
        )

        consecutive_off_red = self.get_count_consecutive(df.tail(20), 'sub')
        off_red_start_idx = len(df) - consecutive_off_red - 1
        pre_off_red_row = df.iloc[off_red_start_idx] if off_red_start_idx >= 0 else None

        sell_cond_2 = (
            pre_close > srb_sup
            and cur_sqz_status == 'off'
            and cur_sqz_hcolor == 'red'
            and consecutive_off_red <= 1
            and pre_off_red_row is not None
            and pre_off_red_row['sqz_status'] == 'on'
            and pre_off_red_row['sqz_id'] >= min_sqz_bars
        )

        down_sup_count = sum([close_t4 < srb_sup, close_t5 < srb_sup, close_t6 < srb_sup])

        if sell_cond_1 and down_sup_count == 0:
            sell_release = '支撑释放'
        elif sell_cond_2:
            sell_release = '已过亮红'
        else:
            sell_release = None

        if buy_release and cur_close >= srb_res:
            signal, release, srb_lab = 'long', buy_release, 'res'
        elif sell_release and cur_close <= srb_sup:
            signal, release, srb_lab = 'short', sell_release, 'sup'
        else:
            signal, release, srb_lab = 'no', '⚪', '⚪'

        price_sequence, trend_sequence, pct_sequence = '⚪', '⚪', '⚪'
        bars_since_anchor, range_pct = '⚪', '⚪'

        if signal != 'no':
            p_seq, t_seq, pct_seq = self.get_sequence_values(df, srb_lab)
            b_stats, r_pct = self.get_anchor_stats(df, srb_lab)

            if signal == 'long':
                if cur_row['ema'] >= cur_close or t_seq.count('高') >= 3:
                    signal = 'no'
            elif signal == 'short':
                if cur_row['ema'] <= cur_close or t_seq.count('低') >= 3:
                    signal = 'no'

            if signal != 'no':
                price_sequence, trend_sequence, pct_sequence = p_seq, t_seq, pct_seq
                bars_since_anchor, range_pct = b_stats, r_pct

        tr, ts = [], []
        for i in range(6, 0, -1):
            row = df.iloc[-(i + 1)]
            tr.append("高" if row['close'] > cur_row['srb_res'] else "低")
            ts.append("高" if row['close'] > cur_row['srb_sup'] else "低")

        if "long" in signal:
            squeeze_bars = f"{int(pre_row['sqz_id']):02d}"
            trend = "".join(tr)
            bb_score = self.get_bb_squeeze_score(df, int(pre_row['sqz_id']))
        elif "short" in signal:
            squeeze_bars = f"{int(pre_row['sqz_id']):02d}"
            trend = "".join(ts)
            bb_score = self.get_bb_squeeze_score(df, int(pre_row['sqz_id']))
        else:
            squeeze_bars = "⚪"
            trend = "⚪"
            bb_score = "⚪"

        return {
            "signal": signal,
            "extra": {
                "release": release,
                "trend_sequence": trend_sequence,
                "price_sequence": price_sequence,
                "pct_sequence": pct_sequence,
                "bars_since_anchor": bars_since_anchor,
                "range_pct": range_pct,
                "squeeze_bars": squeeze_bars,
                "bb_score": bb_score,
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
            signal = "long" if direction == "up" else "watch_long"

        elif rsi_now > 80:
            rsi_desc = "极端超买" if rsi_now > 85 else "严重超买"
            signal = "short" if direction == "down" else "watch_short"

        return {
            "signal": signal,
            "extra": {
                "rsi_info": f"{rsi_desc}（{round(rsi_now, 2)}）{direction}"
            }
        }

    @staticmethod
    def _run_utb_strategy(df: pd.DataFrame, strategy_params: dict) -> Dict[str, Any]:
        _strategy_params = strategy_params

        cur_row = df.iloc[-1]

        utb_signal = cur_row['utb_signal']
        tma_trend = cur_row['t3_trend']
        stc_trend = cur_row['stc_trend']
        stc_value = cur_row['stc']

        signal = "no"
        # if utb_signal == 'buy' and tma_trend == 'bull' and stc_trend == 'bull' and stc_value <= 25:
        #     signal = "long"
        # elif utb_signal == 'sell' and tma_trend == 'bear' and stc_trend == 'bear' and stc_value >= 75:
        #     signal = "short"

        if utb_signal == 'buy':
            signal = "long"
        elif utb_signal == 'sell':
            signal = "short"

        return {
            "signal": signal,
            "extra": {
            }
        }

    def _standardize_output(self, df: pd.DataFrame, strategy_res: dict, strategy_params: dict, symbol: str,
                            interval: str) -> Dict[str, Any]:
        cur = df.iloc[-1]

        parameters = {
            "utb": {"key_value": strategy_params['key_value'], "atr_period": strategy_params['atr_period'], "use_ha": strategy_params['use_ha']},
            "stc": {"stc_length": strategy_params['stc_length'], "stc_fast_length": strategy_params['stc_fast_length'], "stc_slow_length": strategy_params['stc_slow_length'], "stc_factor": strategy_params['stc_factor']},
            "tma": {"tma_fast_length": strategy_params['tma_fast_length'], "tma_slow_length": strategy_params['tma_slow_length'], "tma_vfactor": strategy_params['tma_vfactor']},
            "sqz": {"bb_length": strategy_params['bb_length'], "bb_mult": strategy_params['bb_mult'], "kc_length": strategy_params['kc_length'], "kc_mult": strategy_params['kc_mult'], "min_sqz_bars": strategy_params['min_sqz_bars']},
            "r&s": {"srb_left": strategy_params['srb_left'], "srb_right": strategy_params['srb_right']},
            "ema": {"ema_length": strategy_params['ema_length']},
            "rsi": {"rsi_length": strategy_params['rsi_length'], "rsi_ma_length": strategy_params['rsi_ma_length'], "rsi_smooth": strategy_params['rsi_smooth']},
            "adx": {"adx_length": strategy_params['adx_length'], "adx_threshold": strategy_params['adx_threshold']},
            "atr": {"atr_length": strategy_params['atr_length'], "atr_mult": strategy_params['atr_mult'], "atr_smooth": strategy_params['atr_smooth']},
            "macd": {"cm_fast_length": strategy_params['cm_fast_length'], "cm_slow_length": strategy_params['cm_slow_length'], "cm_signal_length": strategy_params['cm_signal_length']}
        }

        if "long" in strategy_res["signal"]:
            atr = self.format_price(cur['atr_long_stop'])
        elif "short" in strategy_res["signal"]:
            atr = self.format_price(cur['atr_short_stop'])
        else:
            atr = "⚪"

        return {
            "strategy_name": strategy_res["strategy_name"],  # 策略名称
            "signal": strategy_res["signal"],  # 信号
            "interval": interval,  # 周期
            "date": df.index[-1].strftime("%Y-%m-%d"),  # 日期
            "time": df.index[-1].strftime("%H:%M:%S"),  # 时间
            "symbol": symbol,  # 代码
            "price": self.format_price(cur['close']),  # 现格
            "change": round(float(cur['change'] * 100), 2),  # 涨幅
            "ema": self.format_price(cur['ema']),  # ema
            "rsi": round(float(cur['rsi']), 4),  # rsi
            "adx": round(float(cur['adx']), 4),  # adx
            "adx_threshold": int(cur['adx_threshold']),  # adx基准
            "support": self.format_price(cur['srb_sup']),  # 支撑
            "resistance": self.format_price(cur['srb_res']),  # 压力
            "atr_short_stop": self.format_price(cur['atr_short_stop']),  # 做空止损
            "atr_long_stop": self.format_price(cur['atr_long_stop']),  # 做多止损
            "atr": atr,  # 止损
            "parameters": parameters,  # 指标参数

            "extra": strategy_res.get("extra", {})  # 扩展字段
        }

    def execute(self, df: pd.DataFrame, symbol: str, interval: str):
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
                logger.error(f"❌ Strategy {strategy_name} execution error: {e}")


class NotifyEngine:
    def __init__(self, notify_cfg: dict):
        self.cfg = notify_cfg
        self.running_tasks = []

    def process_results(self, results: list, interval: str):
        results_list = [r for r in results if r is not None]
        if not results_list:
            return

        signals = [r for r in results_list if r.get('signal') != "no"]

        if self.cfg.get('console_enable'):
            logger.info(
                f"[{interval}] Scan complete | Instruments monitored: {len(results_list)} | Signals triggered: {len(signals)}")
            for item in results_list:
                symbol = item.get('symbol')
                json_str = json.dumps(item, ensure_ascii=False)
                log_prefix = f"[{interval}] {symbol.ljust(20)}"
                if item.get('signal') != "no":
                    logger.info(f"{log_prefix} | Y | {json_str}")
                else:
                    logger.info(f"{log_prefix} | N | {json_str}")

        if self.cfg.get('tg_enable') and signals:
            task = asyncio.create_task(self.tg_broadcast_and_send(signals, interval))
            self.running_tasks.append(task)
            task.add_done_callback(lambda t: self.running_tasks.remove(t) if t in self.running_tasks else None)

        if self.cfg.get('wecom_enable') and signals:
            task = asyncio.create_task(self.wecom_broadcast_and_send(signals, interval))
            self.running_tasks.append(task)
            task.add_done_callback(lambda t: self.running_tasks.remove(t) if t in self.running_tasks else None)

    @staticmethod
    def format_single_signal(res, tag):
        item = MsgUtils.build_row(res)

        strategy_name = item[0]
        interval = item[1].upper()
        date_str = item[2]
        time_str = item[3]
        tv_symbol = item[4].upper().replace("-SWAP", "").replace("-", "").replace(" ", "")
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

        release = extra_map.get("类型", "⚪")
        trend_sequence = extra_map.get("高低", "⚪")
        pct_sequence = extra_map.get("相距", "⚪")
        bars_since_anchor = extra_map.get("宽度", "⚪")
        range_pct = extra_map.get("深度", "⚪")
        squeeze_bars = extra_map.get("挤压", "⚪")
        ksj = f"k {bars_since_anchor} | j {squeeze_bars} | s {range_pct}"
        bb_score = extra_map.get("分数", "⚪")

        rsi_info = extra_map.get("强弱", "⚪")

        parameters = json.loads(item[12])

        sqz_data = parameters.get("sqz", {})
        sqz_val = " ".join(
            [f"{sqz_data.get(k)}" for k in ["bb_length", "bb_mult", "kc_length", "kc_mult"] if k in sqz_data])

        rs_data = parameters.get("r&s", {})
        rs_val = " ".join([f"{rs_data.get(k)}" for k in ["srb_left", "srb_right"] if k in rs_data])

        adx_data = parameters.get("adx", {})
        adx_val = " ".join([f"{adx_data.get(k)}" for k in ["adx_threshold"] if k in adx_data])

        ema_data = parameters.get("ema", {})
        ema_val = " ".join([f"{ema_data.get(k)}" for k in ["ema_length"] if k in ema_data])

        atr_data = parameters.get("atr", {})
        atr_val = " ".join([f"{atr_data.get(k)}" for k in ["atr_mult"] if k in atr_data])

        utb_data = parameters.get("utb", {})
        utb_val = " ".join([f"{utb_data.get(k)}" for k in ["key_value", "atr_period", "use_ha"] if k in utb_data])

        rsi_data = parameters.get("utb", {})
        rsi_val = " ".join([f"{utb_data.get(k)}" for k in ["rsi_length", "rsi_ma_length"] if k in rsi_data])

        parameters_sqz = f"sqz {sqz_val} | r&s {rs_val}"
        parameters_utb = f"utb {utb_val}"
        parameters_rsi = f"rsi {rsi_val}"
        parameters_con = f"adx {adx_val} | ema {ema_val} | atr {atr_val}"

        is_tg = (tag == "telegram")
        is_wecom = (tag == "wecom")

        if not (is_tg or is_wecom):
            logger.error("❌ No corresponding message card found. Please check.")
            return None

        link = f'<a href="{tv_url}">{tv_symbol}</a>' if is_tg else f'[{tv_symbol}]({tv_url})'
        b_open = "<b>" if is_tg else ""
        b_close = "</b>" if is_tg else ""
        c_open = "<code>" if is_tg else ""
        c_close = "</code>" if is_tg else ""

        is_sqz = "sqz" in strategy_name.lower()

        sqz_block = (
            f"📢 {b_open}类型:{b_close} {c_open}{release}{c_close}\n"
            f"📊 {b_open}高低:{b_close} {c_open}{trend_sequence}{c_close}\n"
            f"📶 {b_open}相距:{b_close} {c_open}{pct_sequence}{c_close}\n"
            f"↔️ {b_open}结构:{b_close} {c_open}{ksj}{c_close}\n"
            f"💯 {b_open}分数:{b_close} {c_open}{bb_score}{c_close}\n"
        ) if is_sqz else ""

        sqz_parameters = (
            f"📍 {b_open}参数:{b_close} {c_open}{parameters_sqz}{c_close}\n"
        ) if is_sqz else ""

        is_utb = "utb" in strategy_name.lower()

        utb_parameters = (
            f"📍 {b_open}参数:{b_close} {c_open}{parameters_utb}{c_close}\n"
        ) if is_utb else ""

        is_rsi = "rsi" in strategy_name.lower()

        rsi_block = (
            f"📐 {b_open}强弱:{b_close} {rsi_info}\n"
        ) if is_rsi else ""

        rsi_parameters = (
            f"📍 {b_open}参数:{b_close} {c_open}{parameters_rsi}{c_close}\n"
        ) if is_rsi else ""

        msg_text = (
            f"🎯 {b_open}策略:{b_close} {c_open}{strategy_name}{c_close}\n"
            f"💹 {b_open}代码:{b_close} {b_open}{link}【{interval}】{b_close}\n"
            f"💰 {b_open}价格:{b_close} {c_open}{price_str}{change_str}{c_close}\n"
            f"✂️ {b_open}止损:{b_close} {c_open}{atr}{c_close}\n"
            f"💸 {b_open}信号:{b_close} {c_open}{signal_text}{c_close}\n"
            f"🔄 {b_open}时间:{b_close} {c_open}{time_str}（UTC+8）{c_close}\n"

            f"{sqz_block}"
            f"{rsi_block}"

            f"⚖️ {b_open}判断:{b_close} {c_open}{judge_text}{c_close}\n"
            f"📅 {b_open}日期:{b_close} {c_open}{date_str}{c_close}\n"

            # f"{sqz_parameters}"
            # f"{utb_parameters}"
            # f"{rsi_parameters}"
            # f"📍 {b_open}参数:{b_close} {c_open}{parameters_con}{c_close}"
        )

        return msg_text

    async def tg_broadcast_and_send(self, signal_results, interval, tag="telegram"):
        token = self.cfg.get('tg_token')
        chat_id = self.cfg.get('tg_chat_id')
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        chunk_size = 10

        total_signals = len(signal_results)

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(signal_results), chunk_size):
                chunk = signal_results[i:i + chunk_size]

                header = (
                    f"🟠 <b>超短【{interval.upper()}】周期</b>\n"
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
                            logger.error(f"❌ telegram send failed [{resp.status}]: {await resp.text()}")
                except Exception as e:
                    logger.error(f"❌ telegram network error: {e}")

                await asyncio.sleep(0.5)

        logger.info(f"[{interval}] telegram notifications sent successfully | Total signals: {total_signals}")

    async def wecom_broadcast_and_send(self, signal_results, interval, tag="wecom"):
        webhook_url = self.cfg.get('wecom_webhook')
        if not webhook_url:
            return

        chunk_size = 5

        total_signals = len(signal_results)

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(signal_results), chunk_size):
                chunk = signal_results[i:i + chunk_size]

                header = (
                    f"🟠 超短【{interval.upper()}】周期\n"
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
                        resp_text = await resp.text()
                        logger.info(f"wecom batch {i // chunk_size + 1}: status={resp.status}, resp={resp_text}")
                        if resp.status != 200:
                            logger.error(f"❌ wecom send failed [{resp.status}]: {await resp.text()}")
                except Exception as e:
                    logger.error(f"❌ wecom network error: {e}")

                await asyncio.sleep(0.5)

        logger.info(f"[{interval}] wecom notification sent | Total signals: {total_signals}")

    async def send_error_msg(self, error_text: str):
        tasks = []

        if self.cfg.get('wecom_enable'):
            webhook_url = self.cfg.get('wecom_webhook')
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"⚠️ **huggingface异常报警**\n\n> 详情: {error_text}\n> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            }
            tasks.append(asyncio.create_task(self._post_request(webhook_url, payload, "wecom_err")))

        if self.cfg.get('tg_enable'):
            token = self.cfg.get('tg_token')
            chat_id = self.cfg.get('tg_chat_id')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": f"⚠️ <b>huggingface异常报警</b>\n\n详情: {error_text}",
                "parse_mode": "HTML"
            }
            tasks.append(asyncio.create_task(self._post_request(url, payload, "tg_err")))

        if tasks:
            await asyncio.gather(*tasks)

    async def send_heartbeat(self):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = (
            f"💓【超短】{now_str}"
        )

        tasks = []

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
            tg_msg = msg.replace("**", "<b>").replace("**", "</b>")
            payload = {
                "chat_id": chat_id,
                "text": tg_msg,
                "parse_mode": "HTML"
            }
            tasks.append(asyncio.create_task(self._post_request(url, payload, "tg_hb")))

        if tasks:
            await asyncio.gather(*tasks)
            logger.info("💓 System heartbeat notification sent")

    @staticmethod
    async def _post_request(url, payload, tag):
        async with aiohttp.ClientSession() as session:
            try:
                if "msgtype" in payload:
                    await session.post(url, json=payload, timeout=5)
                else:
                    await session.post(url, data=payload, timeout=5)
            except Exception as e:
                logger.error(f"❌ Alert send failed [{tag}]: {e}")


class TimeEngine:

    @staticmethod
    def get_wait_seconds(interval: str) -> float:
        now = datetime.now()
        val = int(interval[:-1])
        unit = interval[-1].lower()

        if unit == 'm':
            offset_sec = 10
        elif unit == 'h':
            offset_sec = 30
        elif unit == 'd':
            offset_sec = 60
        else:
            offset_sec = 5

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

        next_run = base_time + timedelta(seconds=offset_sec)

        wait_sec = (next_run - now).total_seconds()

        return wait_sec if wait_sec > 0 else 1.0


class ScanEngine:
    def __init__(self, cfg: dict):
        self.is_active = True
        self.cfg = cfg
        self.data_e = DataEngine(cfg['api'])
        self.ind_e = IndicatorEngine(cfg['strategy'])
        self.strat_e = StrategyEngine(cfg['strategy'])
        self.notify_e = NotifyEngine(cfg['notify'])
        self.timer_e = TimeEngine()
        self.ui_e = UIEngine(cfg)

    async def _proc_symbol(self, session, symbol, interval, sem):
        async with sem:
            try:
                raw = await self.data_e.fetch_klines(session, symbol, interval)

                if raw is None:
                    logger.error(f"❌ {symbol} data fetch failed (empty API response)")
                    return None

                data_len = len(raw)

                cfg_group = self.cfg['strategy'].get("indicators", {})
                if interval.upper() not in cfg_group:
                    raise ValueError(f"❌ Invalid interval [{interval}]: not present in indicators config")
                indicators_params = cfg_group[interval.upper()]
                ema_length = int(indicators_params["ema_length"])

                if data_len < ema_length:
                    logger.warning(f"⚠️ {symbol} insufficient data: {data_len} rows (minimum required: {ema_length})")
                    return None

                df = self.ind_e.calculate(raw, interval)

                res = self.strat_e.execute(df, symbol, interval)

                return res

            except Exception as e:
                logger.error(f"❌ {symbol} processing crashed: {e}", exc_info=True)
                return None

    async def scan_cycle(self, session, symbols, interval):
        sem = asyncio.Semaphore(self.cfg['api']['max_concurrent'])
        tasks = [self._proc_symbol(session, s, interval, sem) for s in symbols]

        raw_iterators = await asyncio.gather(*tasks)

        results = []
        for it in raw_iterators:
            if it:
                results.extend(list(it))

        valid_results = [r for r in results if r is not None]
        signals = [r for r in valid_results if r.get('signal') != "no"]
        try:
            self.ui_e.update_state(valid_results, signals, interval)
        except Exception as ui_err:
            logger.error(f"❌️ UI engine state update failed: {ui_err}")

        self.notify_e.process_results(results, interval)

        if self.notify_e.running_tasks:
            await asyncio.gather(*self.notify_e.running_tasks)

        return valid_results

    async def interval_worker(self, session, interval):
        logger.info(f"🟢 [{interval}] Periodic monitoring task started")

        last_run_slot = None

        while True:
            if not self.is_active:
                logger.critical(
                    f"🛑 [{interval}] System halted due to circuit breaker trigger. Please check token validity and restart the script manually.")
                break

            wait_sec = self.timer_e.get_wait_seconds(interval)
            if wait_sec > 0:
                if wait_sec > 10:
                    target_time = (datetime.now() + timedelta(seconds=wait_sec)).strftime('%H:%M:%S')
                    logger.info(f"💤 [{interval}] Next alignment point: {target_time} (waiting {int(wait_sec)}s)")
                await asyncio.sleep(wait_sec)

            current_slot = datetime.now().replace(second=0, microsecond=0)
            if last_run_slot == current_slot:
                await asyncio.sleep(1)
                continue

            try:
                start_time = time.time()
                watch_list = self.cfg.get("watch_list", [])

                if watch_list:
                    symbols = [self.data_e.format_symbol(s) for s in watch_list]
                else:
                    symbols = await self.data_e.get_active_symbols(session)

                if not symbols:
                    reason = "关键异常：无法获取活跃币种列表（接口返回为空）。"
                    await self._trigger_circuit_breaker(interval, reason)
                    continue

                valid_results = await self.scan_cycle(session, symbols, interval)

                if len(symbols) > 0 and (valid_results is None or len(valid_results) == 0):
                    reason = "关键异常：所有币种详情请求均失败"
                    await self._trigger_circuit_breaker(interval, reason)
                    continue

                last_run_slot = current_slot
                logger.info(
                    f"✅ [{interval}] Scan done (valid: {len(valid_results)}), time: {time.time() - start_time:.2f}s")

            except Exception as e:
                logger.error(f"❌ [{interval}] Runtime error: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def heartbeat_worker(self):
        logger.info("💓 Heartbeat task started (cycle: 4 hours)")

        await self.notify_e.send_heartbeat()

        while True:
            try:
                await asyncio.sleep(4 * 3600)

                if self.is_active:
                    await self.notify_e.send_heartbeat()
                else:
                    logger.warning("💓 Heartbeat skipped: system is in circuit breaker state.")

            except Exception as e:
                logger.error(f"❌ Heartbeat task exception: {e}")
                await asyncio.sleep(60)

    async def _trigger_circuit_breaker(self, interval: str, reason: str):
        self.is_active = False
        error_msg = (
            f"🛑 【系统熔断停机】\n"
            f"触发周期: {interval}\n"
            f"故障原因: {reason}\n"
            f"结果: 扫描任务已终止"
        )
        logger.critical(error_msg)
        await self.notify_e.send_error_msg(error_msg)

    async def run(self):
        async with aiohttp.ClientSession() as session:
            try:
                logger.info("⚡ Start immediate scan")

                watch_list = self.cfg.get("watch_list", [])

                if watch_list and len(watch_list) > 0:
                    symbols = [self.data_e.format_symbol(s) for s in watch_list]
                    logger.info(f"📋 Using configuration list (converted format): {symbols}")
                else:
                    symbols = await self.data_e.get_active_symbols(session)

                if not symbols or len(symbols) == 0:
                    error_msg = "🚨 Program startup failed: request data is empty, cannot perform initial scan"
                    logger.critical(f"❌ {error_msg}")
                    await self.notify_e.send_error_msg(error_msg)
                    return

                await self.scan_cycle(session, symbols, self.cfg.get("intervals")[0])

            except Exception as e:
                logger.error(f"❌ Initial scan crashed: {e}", exc_info=True)

            workers = [self.interval_worker(session, i) for i in self.cfg.get('intervals')]

            workers.append(self.heartbeat_worker())

            await asyncio.gather(*workers)


class UIEngine:
    def __init__(self, cfg: dict):
        self.cfg = cfg.get('ui', {})
        self.router = cfg.get('strategy', {}).get('router', {})
        self.signals_by_strategy = {key: [] for key in self.router.keys()}
        self.market_snapshot = []
        self.last_update = "尚未开始"
        self.log_stream = []

        self.theme_css = """
            .gradio-container { 
                background-color: #f7f9fc !important; 
            }

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

            .stat-card { 
                background: #ffffff !important; 
                padding: 16px !important;
                border-radius: 12px !important;
                border: 1px solid #e1e4e8 !important;
            }

            .stat-box, .log-box { 
                background-color: #f0f2f5 !important; 
                color: #0066cc !important; 
                font-family: 'Fira Code', monospace !important; 
                padding: 12px !important;
                border-radius: 8px !important;
                border: 1px solid #d1d5da !important;
                min-height: 100px;
            }

            #sig-table-sqz, #sig-table-utb, #sig-table-rsi, #market-table { 
                background: white !important; 
                border-radius: 12px !important; 
                overflow: visible !important; 
            }

            #sig-table-sqz, #sig-table-utb, #sig-table-rsi, #market-table {
                max-height: 1200px !important;
                overflow-y: auto !important;
                border: 1px solid #e1e4e8 !important;
            }
        """

    def update_state(self, all_results, signal_results, interval):
        self.last_update = datetime.now().strftime("%H:%M:%S")

        for item in all_results:
            item['interval'] = interval

        self.market_snapshot = all_results

        if signal_results:
            for s in signal_results:
                s['interval'] = interval
                strat = s.get('strategy_name').lower()

                if strat not in self.signals_by_strategy:
                    self.signals_by_strategy[strat] = []

                self.signals_by_strategy[strat] = ([s] + self.signals_by_strategy[strat])[:100]

        log_msg = f"[{interval}] 扫描完成 | 时间: {self.last_update} | 信号: {len(signal_results)} | 监控总数: {len(all_results)}"

        if signal_results:
            signal_details = [
                f"{s['symbol'].split('-')[0]}({s.get('strategy_name')})"
                for s in signal_results
            ]

            log_msg += f" (发现: {', '.join(signal_details)})"

        self.log_stream.insert(0, log_msg)

        self.log_stream = self.log_stream[:20]

    def _refresh_logic(self):
        ordered_keys = list(self.router.keys())
        result = []
        for key in ordered_keys:
            if self.router.get(key, {}).get("enabled", False):
                rows = [MsgUtils.build_row(item) for item in self.signals_by_strategy.get(key, [])]
                result.append(rows)

        market_rows = [MsgUtils.build_row(item) for item in self.market_snapshot if item]

        if self.market_snapshot:
            sample = self.market_snapshot[0]
            status_info = f"<span>【{sample.get('interval')}】数据点: {sample.get('date')} {sample.get('time')[:5]} | 刷新时间: {self.last_update}</span>"
        else:
            status_info = f"<span>等待数据同步... | 系统时间: {self.last_update}</span>"

        status_info_html = f"<div class='stat-box'>{status_info}</div>"
        log_html = f"<div class='log-box'>{''.join([f'<div>> {m}</div>' for m in self.log_stream])}</div>"

        return *result, market_rows, status_info_html, log_html

    def create_demo(self):
        with gr.Blocks() as demo:
            gr.HTML(
                f"""<div class="header-wrapper"><h1 class="header-title">{self.cfg.get("ui_name")}</h1></div>""")

            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group(elem_classes="stat-card"):
                        gr.Markdown("### ⏳ 最新状态")
                        status_display = gr.HTML(value="<div class='stat-box'>>> 等待扫描...</div>")

                with gr.Column(scale=3):
                    with gr.Group(elem_classes="stat-card"):
                        gr.Markdown("### 🔄 扫描日志")
                        log_display = gr.HTML(value="<div class='log-box'>>> 系统启动中...</div>")

            table_headers = ["策略", "周期", "日期", "时间", "代码", "图表", "信号", "现价", "涨幅", "止损", "判断",
                             "其他", "参数"]

            column_widths = ["100px", "60px", "120px", "80px", "150px", "60px", "100px", "120px", "80px", "120px",
                             "240px",
                             "1600px", ]

            tab_configs = [
                (key, f"{cfg.get('icon', '🎯')} {key}信号", f"sig-table-{key}")
                for key, cfg in self.router.items()
            ]

            table_refs = {}
            market_table = None

            with gr.Tabs(elem_classes="tabs"):
                for strat_key, tab_label, elem_id in tab_configs:
                    if not self.router.get(strat_key, {}).get("enabled", False):
                        continue
                    with gr.TabItem(tab_label):
                        table_refs[strat_key] = gr.DataFrame(
                            headers=table_headers,
                            column_widths=column_widths,
                            datatype="markdown",
                            elem_id=elem_id,
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

            ordered_keys = list(self.router.keys())
            dynamic_outputs = [table_refs[k] for k in ordered_keys if k in table_refs]
            dynamic_outputs += [market_table, status_display, log_display]

            gr.Timer(self.cfg.get("refresh_interval", 5)).tick(
                fn=self._refresh_logic,
                outputs=dynamic_outputs
            )

        demo.custom_css = self.theme_css

        return demo


class RunEngine:
    def __init__(self, config: Dict):

        self._setup_timezone()

        self.config = config

        self.local_key = self._load_initial_config()

        self.env_key = os.getenv("ENCRYPTION_KEY")

        self.final_key = self.env_key or self.local_key

        if not self.final_key:
            raise ValueError("❌ Critical: encryption_key not found")

        self.cipher = Fernet(self.final_key.encode())

        self._setup_credentials()

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
            logger.warning("⚠️ Local config file not found. Switching to environment mode.")
            return None

    def _setup_credentials(self):
        try:
            wecom_webhook = b'gAAAAABpX1lf_OZccl6JYh14FJlLEmJDtV37L1jW5MMRhdA09xypIujad5g1e2axJUwOA_gKCF3kodoYVG9Wrj1TyayLXmSn3t6lnG5xzNXedE01dNq1E-S77oYFLhaS9g3Ay24P2apcvBGkaV61cI76Pk7jNrjRTNjhxwgrvT3FiDHaQk3FULbFwvQJy0BADgv1cli4_vzB'
            tg_token = b'gAAAAABpX1mGV2Aqsf_W0eXjohhjNzWB4pDhsPqRDDei9jfKMkwsCT9Bu0qHzOGDAaapiBGNPwP1hyk46SN78yq2si5RylJTSBmdh6wPJlWpeAZtlEgu7wuxlEi3AMByECDdWnBx1iol'
            tg_chat_id = b'gAAAAABpX1maZKmpePVf4ancQG2QpOX7YXk4wPMqPTw8x4DgJN3cKaVO6I0cQp0eCpL1gR4lim2W6k0LWXqH-R28889G2I446Q=='

            self.config["notify"]["wecom_webhook"] = self.cipher.decrypt(wecom_webhook).decode()
            self.config["notify"]["tg_token"] = self.cipher.decrypt(tg_token).decode()
            self.config["notify"]["tg_chat_id"] = self.cipher.decrypt(tg_chat_id).decode()

        except Exception as e:
            logger.error(f"❌ Failed to decrypt credentials. Verify that encryption_key is valid: {e}")
            raise

    @staticmethod
    async def _handle_health(_request):
        return web.Response(text="Bot is running", content_type='text/html')

    async def _run_services(self):
        await asyncio.gather(self.scan_engine.run())

    async def run_huggingface(self):

        demo = self.scan_engine.ui_e.create_demo()

        scan_task = asyncio.create_task(self.scan_engine.run())

        await asyncio.sleep(0.5)

        logger.info("🚀 Starting gradio interface on port 7860...")

        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            css=self.scan_engine.ui_e.theme_css,
            theme=gr.themes.Soft(),
            prevent_thread_lock=True
        )

        try:
            await scan_task
        except Exception as e:
            logger.error(f"❌ Scanning task terminated unexpectedly: {e}")

    async def run_local(self):
        logger.info("✅ Local mode: starting engines")
        await self._run_services()

    def start(self):
        try:
            if self.env_key:
                asyncio.run(self.run_huggingface())
            else:
                asyncio.run(self.run_huggingface())
        except KeyboardInterrupt:
            logger.warning("⚠️ Stopped by user")
        except Exception as e:
            logger.error(f"❌ Critical error: {e}")


class MsgUtils:
    extra_key_map = {
        # sqz
        "release": "类型",
        "price_sequence": "阶梯",
        "trend_sequence": "高低",
        "pct_sequence": "相距",
        "bars_since_anchor": "宽度",
        "range_pct": "深度",
        "squeeze_bars": "挤压",
        "trend": "趋势",
        "bb_score": "分数",

        "changes": "走势",
        "changes_str": "涨幅",
        "sqz_status": "释放",
        "macd": "水平",
        "rsi_info": "强弱"
    }

    @staticmethod
    def build_row(res):
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
        raw_signal = res.get('signal')
        atr = res.get('atr')
        parameters = json.dumps(res.get('parameters'), ensure_ascii=False)

        if rsi >= 70:
            i_b = "📈rsi"
        elif rsi <= 30:
            i_b = "📉rsi"
        else:
            i_b = "🗒️rsi"

        raw_sig = str(raw_signal).lower()
        if raw_sig == "long":
            signal_text = "🟢 long"
        elif raw_sig == "short":
            signal_text = "🔴 short"
        elif raw_sig == "watch_long":
            signal_text = "🟠 long"
        elif raw_sig == "watch_short":
            signal_text = "🟠 short"
        else:
            signal_text = "⚪"

        e_b = "📈ema" if price > ema else "📉ema"
        a_b = "📈adx" if adx > adx_threshold else "📉adx"
        judge_text = f"{e_b} {a_b} {i_b}"

        active_exchange = CONFIG["api"].get("active_exchange")
        tv_symbol = symbol.replace("-SWAP", "").replace("-", "")
        if active_exchange == "b":
            tv_url = f"https://cn.tradingview.com/chart/?symbol=BINANCE%3A{tv_symbol}"
        else:
            tv_url = f"https://cn.tradingview.com/chart/?symbol=OKX%3A{tv_symbol}.P"

        tv_link = f"[📊]({tv_url})"

        def _format_extra(data):
            parts = []
            for k, v in data.items():
                name = MsgUtils.extra_key_map.get(k, k)
                val_s = (str(v)
                         .replace("lime", "🟢")
                         .replace("green", "🟢")
                         .replace("red", "🔴")
                         .replace("maroon", "🔴")
                         .replace("高", "⬆️")
                         .replace("低", "⬇️")
                         .replace("涨", "📈")
                         .replace("跌", "📉")
                         .replace("平", "🗒")
                         .replace("off", "⚪")
                         .replace("on", "⚫"))
                val_s = re.sub(r"\[.*?]", "", val_s)
                parts.append(f"{name}: {val_s}")
            return " ".join(parts)

        format_extra = _format_extra(res.get('extra'))

        return [
            strategy_name,  # 0策略
            interval,  # 1周期
            date_str,  # 2日期
            time_str[:5],  # 3时间
            symbol,  # 4代码
            tv_link,  # 5图表
            signal_text,  # 6信号
            price_str,  # 7现价
            f"{change}%",  # 8涨幅
            atr,  # 9止损
            judge_text,  # 10判断
            format_extra,  # 11其他
            parameters  # 12参数【一定放在最后一行】
        ]


if __name__ == "__main__":
    runner = RunEngine(CONFIG)
    runner.start()