#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import datetime
import pandas as pd
import akshare as ak

from conf.config import PATH_CONFIG, INDICATOR_CONFIG
from core.util.decorator import retry

class StockListManager:
    def __init__(self, db_client=None):
        self.db_client = db_client
        self.cache_file = PATH_CONFIG["CACHE_FILE"]

    def get_stock_list(self):
        """获取原始名单（优先读缓存）"""
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        df_raw = pd.DataFrame()

        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)

                if cache.get("time") == today_str:
                    print(f"🗄️ [系统] 使用全量标的缓存")
                    df_raw = pd.DataFrame(cache["data"])
            except Exception as e:
                print(f"⚠️ [警告] 缓存读取异常 {e}")

        if df_raw.empty:
            print("🔍 [系统] 缓存失效 正获取全量标的...")
            df_raw = self.fetch_stock_list_safe()

            self._save_to_cache(df_raw, today_str)

        df_filtered = self._apply_exclude_rules(df_raw)

        return df_filtered

    @staticmethod
    def _apply_exclude_rules(df):
        """板块过滤"""
        if df.empty:
            return df

        exclude_cfg = INDICATOR_CONFIG.get("EXCLUDE", {})
        total_before = len(df)

        # 确保 code 是 6 位字符串格式
        df['code'] = df['code'].astype(str).str.zfill(6)

        # 过滤创业板
        if exclude_cfg.get("EXCLUDE_GEM"):
            df = df[~df['code'].str.startswith(('300', '301'))]

        # 过滤科创板
        if exclude_cfg.get("EXCLUDE_KCB"):
            df = df[~df['code'].str.startswith(('688', '689'))]

        # 过滤北交所
        if exclude_cfg.get("EXCLUDE_BJ"):
            df = df[~df['code'].str.startswith(('8', '4', '9', '43', '83', '87'))]

        # 过滤 ST 和 退市股
        if exclude_cfg.get("EXCLUDE_ST"):
            df = df[~df['name'].str.upper().str.contains("ST|退")]

        print(f"✅ [过滤] 原始 {total_before} 支 -> 滤后 {len(df)} 支")
        return df

    def _save_to_cache(self, df, date_str):
        """股票代码信息写入本地JSON文件"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                cache_data = {
                    "time": date_str,
                    "data": df.to_dict(orient="records")
                }
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"💾 [缓存] 全量标的缓存至 {self.cache_file}")
        except Exception as e:
            print(f"❌ [错误] 缓存写入失败 {e}")

    @retry(max_retries=2, delay=1)
    def fetch_stock_list_safe(self):
        """全市场个股最新代码和名称"""
        try:
            df = ak.stock_info_a_code_name()
            if not df.empty:
                return df[["code", "name"]]
        except Exception as e:
            print(f"❌ [错误] stock_info_a_code_name API 接口失效 {e}")

        return pd.DataFrame()