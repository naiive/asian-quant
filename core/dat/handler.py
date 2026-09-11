#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import pandas as pd
from core.client.api import APIClient
from core.client.mysql import MySQLClient
from conf.config import STRATEGY_CONFIG
from core.dat.manager import StockListManager

class DataHandler:
    def __init__(self):
        self.mysql_client = MySQLClient()
        self.api_client = APIClient()
        self.manager = StockListManager(self.mysql_client)
        self.realtime_cache = None

    def get_target_list(self):
        df = self.manager.get_stock_list()

        return df['code'].tolist() if df is not None else []

    @staticmethod
    def chunk_symbols(symbols_list, size):
        symbols_list = list(symbols_list)
        for i in range(0, len(symbols_list), size):
            yield symbols_list[i: i + size]

    def prepare_realtime_data(self):
        if STRATEGY_CONFIG.get("CN_USE_REAL_TIME_DATA", True):
            print("🚀 [系统] 正在预取全市场实时快照")
            try:
                df = self.api_client.fetch_realtime_snapshot()

                if df is None or df.empty:
                    print("❌ [异常] 实时快照获取为空 请检查网络或API限制")
                    self.realtime_cache = None
                    return

                self.realtime_cache = df.set_index('code').to_dict(orient='index')
                print(f"✅ [系统] 实时数据预取成功 已缓存 {len(self.realtime_cache)} 支")

            except Exception as e:
                print(f"❌ [异常] 预取实时数据崩溃 {e}")
                self.realtime_cache = None

    def get_full_data(self, symbol, target_date):
        df_daily = self.mysql_client.fetch_daily_data(symbol, target_date)

        if df_daily.empty:
            return df_daily

        if not STRATEGY_CONFIG.get("CN_USE_REAL_TIME_DATA") or self.realtime_cache is None:
            return df_daily

        full_df = self._append_snapshot(symbol, df_daily)

        return full_df

    def _append_snapshot(self, symbol, df_daily):
        if not self.realtime_cache or symbol not in self.realtime_cache:
            return df_daily

        today = datetime.datetime.now().date()
        latest_data = self.realtime_cache[symbol]

        last_date = pd.to_datetime(df_daily['date']).dt.date.iloc[-1]
        if last_date >= today:
            return df_daily

        new_row = {
            'date': today,
            'code': symbol,
            'open': latest_data['open'],
            'pct_chg': latest_data['pct_chg'],
            'high': latest_data['high'],
            'low': latest_data['low'],
            'close': latest_data['close'],
            'volume': latest_data['volume'],
            'amount': latest_data['amount']
        }

        return pd.concat([df_daily, pd.DataFrame([new_row])], ignore_index=True)