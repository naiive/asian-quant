#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
import requests
from requests.exceptions import RequestException

from conf.config import SYSTEM_CONFIG
from core.util.decorator import retry

class APIClient:

    def __init__(self):
        self.timeout = SYSTEM_CONFIG.get("REQUEST_TIMEOUT", 20)

    @retry(max_retries=2, delay=1)
    def fetch_realtime_snapshot(self):
        """获取全市场A股实时行情快照"""
        try:
            df_sina = ak.stock_zh_a_spot()
            sina_map = {
                "代码": "code",
                "名称": "name",
                "最新价": "close",
                "涨跌幅": "pct_chg",
                "成交量": "volume",
                "成交额": "amount",
                "今开": "open",
                "最高": "high",
                "最低": "low",
                "时间戳": "time",
            }
            df = df_sina.rename(columns=sina_map)

            if "volume" in df.columns:
                df["volume"] = (
                    pd.to_numeric(df["volume"], errors="coerce") / 100
                )

            missing_cols = ["pe", "mcap", "ffmc", "ytd"]
            for col in missing_cols:
                df[col] = float("nan")
        except Exception as e:
            raise Exception(f"❌【失效】全市场快照接口失效 {e}")

        if "code" in df.columns:
            df["code"] = df["code"].astype(str).str.extract(r"(\d{6})")
            df["code"] = df["code"].str.zfill(6)
        else:
            return pd.DataFrame()

        money_cols = ["mcap", "ffmc"]
        numeric_cols = [
            "open",
            "pct_chg",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "pe",
            "mcap",
            "ffmc",
            "ytd",
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                if col in money_cols:
                    df[col] = (df[col] / 100000000).round(2)

        return df

    @retry(max_retries=2, delay=1)
    def fetch_individual_info(self, symbol: str):
        """获取单只股票基本面信息"""
        try:
            df_raw = ak.stock_individual_info_em(symbol=str(symbol).zfill(6))

            if df_raw is None or df_raw.empty:
                return pd.DataFrame()

            df = df_raw.set_index("item").T.reset_index(drop=True)

            column_map = {
                "代码": "code",
                "股票简称": "name",
                "行业": "industry",
                "总市值": "mcap",
                "流通市值": "ffmc",
            }
            df = df.rename(columns=column_map)
            df["code"] = str(symbol).zfill(6)

            money_cols = ["mcap", "ffmc"]
            for col in money_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    df[col] = (df[col] / 100000000).round(2)

            final_cols = ["code", "name", "industry", "mcap", "ffmc"]
            return df[[c for c in final_cols if c in df.columns]]

        except Exception as e:
            raise Exception(f"❌【失效】股票基本面接口获取失效 {e}")

    @retry(max_retries=2, delay=1)
    def fetch_crypto_market_snapshot(
        self, exchange: str, top_n=300, rank_by="volume", min_volume=500000
    ) -> list[dict]:
        """获取加密货币市场快照，并按照成交量或涨跌幅进行动态筛选排序"""
        pool = []
        raw_data = []

        try:
            if exchange == "O":
                url = base64.b64decode(
                    b"aHR0cHM6Ly93d3cub2t4LmNvbS9hcGkvdjUvbWFya2V0L3RpY2tlcnM="
                ).decode()
                r = requests.get(url, params={"instType": "SWAP"}, timeout=10)
                r.raise_for_status()
                tickers = r.json().get("data", [])

                for t in tickers:
                    inst_id = t.get("instId", "")
                    if inst_id.endswith("-USDT-SWAP"):
                        base = inst_id.split("-")[0]
                        vol_usdt = float(t.get("volCcy24h", 0)) * float(
                            t.get("last", 1)
                        )
                        open_24h = float(t.get("open24h", 0))
                        last_price = float(t.get("last", 0))
                        change = (
                            ((last_price - open_24h) / open_24h)
                            if open_24h > 0
                            else 0.0
                        )

                        raw_data.append(
                            {
                                "code": f"{base}-USDT",
                                "name": base,
                                "volume": vol_usdt,
                                "change": abs(change),
                            }
                        )

            elif exchange == "B":
                url = base64.b64decode(
                    b"aHR0cHM6Ly9mYXBpLmJpbmFuY2UuY29tL2ZhcGkvdjEvdGlja2VyLzI0aHI="
                ).decode()
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                tickers = r.json()

                for t in tickers:
                    symbol = t.get("symbol", "")
                    if symbol.endswith("USDT"):
                        base = symbol[:-4]
                        raw_data.append(
                            {
                                "code": f"{base}-USDT",
                                "name": base,
                                "volume": float(t.get("quoteVolume", 0)),
                                "change": abs(
                                    float(t.get("priceChangePercent", 0)) / 100
                                ),
                            }
                        )

        except Exception as e:
            print(f"⚠️  [快照网络请求失败] 无法拉取行情大盘 [{exchange}]: {e}")

        if not raw_data:
            return []

        try:
            df = pd.DataFrame(raw_data)
            df = df[df["volume"] >= min_volume]

            sort_by_col = "volume" if rank_by == "volume" else "change"
            df = df.sort_values(by=sort_by_col, ascending=False)
            df = df.head(top_n)

            pool = df[["code", "name"]].to_dict(orient="records")
        except Exception as e:
            print(f"⚠️  [快照 DataFrame 过滤失败]: {e}")

        return pool

    @staticmethod
    @retry(max_retries=2, delay=1)
    def fetch_crypto_klines(
        exchange: str,
        symbol: str,
        interval: str,
        limit: int,
        end_time: str | None = None,
    ) -> pd.DataFrame:
        okx_symbol = ""
        bnb_symbol = ""

        try:
            if "-" in symbol:
                base, quote = symbol.split("-")
            else:
                base, quote = symbol[:-4], symbol[-4:]

            if exchange == "O":
                okx_symbol = f"{base}-{quote}-SWAP"
            elif exchange == "B":
                bnb_symbol = f"{base}{quote}"

            end_ts_ms: int | None = None
            if end_time:
                fmt = "%Y-%m-%d %H:%M:%S" if " " in end_time else "%Y-%m-%d"
                dt = datetime.strptime(end_time, fmt)
                if fmt == "%Y-%m-%d":
                    dt = dt.replace(hour=23, minute=59, second=59)
                end_ts_ms = int(dt.timestamp() * 1000)

            if exchange == "O":
                url = base64.b64decode(
                    b"aHR0cHM6Ly93d3cub2t4LmNvbS9hcGkvdjUvbWFya2V0L2NhbmRsZXM="
                ).decode()
                params: dict = {
                    "instId": okx_symbol,
                    "bar": interval,
                    "limit": limit,
                }
                if end_ts_ms:
                    params["after"] = end_ts_ms

                r = requests.get(url, params=params, timeout=10)
                r.raise_for_status()

                k_data = r.json().get("data", [])
                df = pd.DataFrame(
                    k_data,
                    columns=[
                        "ts",
                        "o",
                        "h",
                        "l",
                        "c",
                        "v",
                        "volCcy",
                        "volCcyQuote",
                        "confirm",
                    ],
                )
                df = df.iloc[::-1].reset_index(drop=True)
                df = df[["ts", "o", "h", "l", "c", "v"]].astype(float)
                df.columns = ["ts", "open", "high", "low", "close", "volume"]
                df["date"] = pd.to_datetime(df["ts"], unit='ms') + timedelta(
                    hours=8
                )
                df.set_index("date", inplace=True)
                return df

            elif exchange == "B":
                url = base64.b64decode(
                    b"aHR0cHM6Ly9mYXBpLmJpbmFuY2UuY29tL2ZhcGkvdjEva2xpbmVz"
                ).decode()

                params = {
                    "symbol": bnb_symbol,
                    "interval": interval.lower(),
                    "limit": limit,
                }
                if end_ts_ms:
                    params["endTime"] = end_ts_ms

                r = requests.get(url, params=params, timeout=10)
                r.raise_for_status()

                raw_json = r.json()
                if not raw_json or not isinstance(raw_json, list):
                    return pd.DataFrame()

                cleaned_data = [
                    kline[:6] for kline in raw_json if len(kline) >= 6
                ]
                if not cleaned_data:
                    return pd.DataFrame()

                df = pd.DataFrame(
                    cleaned_data,
                    columns=[
                        "ts",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                    ],
                ).astype(float)
                df["date"] = pd.to_datetime(df["ts"], unit='ms') + timedelta(
                    hours=8
                )
                df.set_index("date", inplace=True)
                return df

            return pd.DataFrame()

        except RequestException as e:
            print(f"[Network Error] {exchange} {symbol}: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"[Error] {exchange} {symbol}: {e}")
            return pd.DataFrame()