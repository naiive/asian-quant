#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
from sqlalchemy import create_engine, text
import pandas as pd

from conf.config import SYSTEM_CONFIG, STRATEGY_CONFIG, TABLE_CONFIG, DB_CONFIG, INDICATOR_CONFIG
from conf.registry import CONDITION_REGISTRY

class MySQLClient:

    def __init__(self):
        c = DB_CONFIG
        self.db_url = (
            f"mysql+pymysql://{c['USER']}:{c['PASS']}@"
            f"{c['HOST']}:{c['PORT']}/{c['DB_NAME']}?"
            f"charset={c['CHARSET']}"
        )

        self.engine = create_engine(
            self.db_url,
            pool_size=SYSTEM_CONFIG.get("DB_POOL_SIZE", 15),
            max_overflow=SYSTEM_CONFIG.get("DB_MAX_OVERFLOW", 25),
            pool_recycle=SYSTEM_CONFIG.get("DB_POOL_RECYCLE", 3600),
        )

        interval = STRATEGY_CONFIG.get("CN_INTERVAL", "daily")

        if interval == "weekly":
            self.kline_table = TABLE_CONFIG.get(
                "QUERY_WEEKLY_TABLE", "asian_quant_stock_weekly"
            )
        elif interval == "monthly":
            self.kline_table = "asian_quant_stock_monthly"
        else:
            self.kline_table = TABLE_CONFIG.get(
                "QUERY_DAILY_TABLE", "asian_quant_stock_daily"
            )

        self.info_table = TABLE_CONFIG.get("QUERY_STOCK_INFO")
        self.indicator_days = INDICATOR_CONFIG.get("DAYS", 220)
        self.adjust = INDICATOR_CONFIG.get("ADJUST", "qfq")

        # 主进程龙虎榜【内存】
        self.lhb_cache = {}
        # 主进程多级类别【内存】
        self.industry_cache = {}

    def upsert_table(
        self, df: pd.DataFrame, table_name: str, primary_keys: list = None
    ):
        """批量UPSERT数据至指定表（支持多主键与增量更新）"""
        if df is None or df.empty:
            return

        pks = primary_keys or ["trade_date", "symbol", "label_params"]
        cols = df.columns.tolist()

        df = df.astype(object).where(pd.notnull(df), None)

        col_names = ", ".join([f"`{c}`" for c in cols])
        placeholders = ", ".join([f":{c}" for c in cols])
        update_stmt = ", ".join(
            [f"`{c}`=VALUES(`{c}`)" for c in cols if c not in pks]
        )
        upset_sql = f"""
            INSERT INTO `{table_name}` ({col_names}) 
            VALUES ({placeholders}) 
            ON DUPLICATE KEY UPDATE {update_stmt}, `update_time` = NOW()
        """

        try:
            data_dicts = df[cols].to_dict(orient="records")
            with self.engine.connect() as conn:
                with conn.begin():
                    conn.execute(text(upset_sql), data_dicts)
            print(f"✅ [成功] upsert {table_name} {len(df)} 行")
        except Exception as e:
            print(f"❌ [失败] upsert {table_name} {e}")

    def query_to_df(self, sql: str, params: dict = None) -> pd.DataFrame:
        """执行 SQL 查询并返回 Pandas DataFrame（支持常规 SQL 及存储过程 CALL）"""
        try:
            stripped = sql.strip().upper()

            if stripped.startswith("CALL"):
                final_sql = sql
                if params:
                    for key, val in params.items():
                        final_sql = final_sql.replace(
                            f":{key}",
                            f"'{val}'" if isinstance(val, str) else str(val),
                        )

                raw_conn = self.engine.raw_connection()
                cursor = None
                try:
                    cursor = raw_conn.cursor()
                    cursor.execute(final_sql.strip())
                    rows = cursor.fetchall()
                    cols = [d[0] for d in cursor.description]
                    return pd.DataFrame(rows, columns=cols)
                finally:
                    if cursor is not None:
                        cursor.close()
                    raw_conn.close()

            with self.engine.connect() as conn:
                return pd.read_sql_query(text(sql), conn, params=params)

        except Exception as e:
            print(f"❌ [失败] query {e}")
            return pd.DataFrame()

    def fetch_daily_data(self, symbol: str, target_date: str):
        """核心方法：获取单标的当前周期的历史 K 线序列并进行内存数据打标

        1. SQL只查询当前周期表(self.kline_table)的 K 线数据
        2. 内存映射行业分类信息
        3. 内存映射龙虎榜【仅在 daily 日线模式下才触发对齐贴标】
        """
        standard_cols = [
            "date",
            "code",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "pct_chg",
            "turnover_rate",
        ]
        ext_cols = [
            "is_lhb",
            "interpretation",
            "list_reason",
            "level1_name",
            "level2_name",
            "level3_name",
        ]

        empty_df = pd.DataFrame(columns=standard_cols + ext_cols)

        query = f"""
            SELECT 
                {", ".join(standard_cols)}
            FROM 
                {self.kline_table}
            WHERE 
                code = :code 
                AND date <= :target_date 
                AND adjust = :adjust
            ORDER BY date DESC 
            LIMIT :limit
        """
        params = {
            "code": symbol,
            "target_date": target_date,
            "adjust": self.adjust,
            "limit": int(self.indicator_days * 1.5),
        }

        try:
            df = self.query_to_df(query, params)

            if df.empty:
                return empty_df

            sw = self.industry_cache.get(symbol, {})
            df["level1_name"] = sw.get("level1_name")
            df["level2_name"] = sw.get("level2_name")
            df["level3_name"] = sw.get("level3_name")

            df["is_lhb"] = "否"
            df["interpretation"] = None
            df["list_reason"] = None

            current_interval = STRATEGY_CONFIG.get("CN_INTERVAL", "daily")

            if current_interval == "daily":
                lhb = self.lhb_cache.get(symbol)
                if lhb:
                    target_dt_str = str(target_date)[:10]
                    mask = df["date"].astype(str).str.startswith(target_dt_str)
                    if mask.any():
                        df.loc[mask, "is_lhb"] = "是"
                        df.loc[mask, "interpretation"] = lhb.get(
                            "interpretation"
                        )
                        df.loc[mask, "list_reason"] = lhb.get("list_reason")
            else:
                pass

            stock_latest = str(df.iloc[0]["date"])[:10]

            if stock_latest != str(target_date)[:10] and not STRATEGY_CONFIG.get("CN_USE_REAL_TIME_DATA", False):
                return empty_df

            return df.iloc[::-1].tail(self.indicator_days).reset_index(drop=True)

        except Exception as e:
            print(f"❌ [异常] {symbol} K线拼接数据 {e}")
            return empty_df

    def get_trade_days_list(self) -> list:
        """获取真实的交易日/交易周期 K 线日期列表"""
        period_str = STRATEGY_CONFIG.get("CN_HISTORY_DAYS")
        is_realtime = STRATEGY_CONFIG.get("CN_USE_REAL_TIME_DATA", False)

        if is_realtime:
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            return [today_str]

        if "~" in str(period_str):
            start_s, end_s = period_str.split("~")
            sql = f"SELECT DISTINCT date as d FROM {self.kline_table} WHERE date BETWEEN :s AND :e ORDER BY date"
            res = self.query_to_df(
                sql, {"s": start_s.strip(), "e": end_s.strip()}
            )
            return (
                pd.to_datetime(res["d"]).dt.strftime("%Y-%m-%d").tolist()
                if not res.empty
                else []
            )

        return [period_str] if period_str else []

    def fetch_future_changes(self, symbol, start_date, lookback_list=None):
        """计算未来 N 个周期（如未来N天/未来N周/未来N月）的累计涨幅（回测辅助穿越指标）"""
        max_limit = max(lookback_list) + 10

        query = f"""
            SELECT 
                date,
                close 
            FROM
                {self.kline_table} 
            WHERE 
                code = :code 
                AND date >= :start_date 
                AND adjust = :adjust
            ORDER BY date 
            LIMIT :limit
        """
        params = {
            "code": symbol,
            "start_date": start_date,
            "adjust": self.adjust,
            "limit": max_limit,
        }

        try:
            df = self.query_to_df(query, params)
            if df.empty or len(df) < 2:
                return None

            base_close = df.iloc[0]["close"]
            res_dict = {"code": symbol, "base_date": df.iloc[0]["date"]}

            for n in lookback_list:
                if len(df) > n:
                    change = (df.iloc[n]["close"] - base_close) / base_close
                    res_dict[f"FC{n}"] = round(change * 100, 2)
                else:
                    res_dict[f"FC{n}"] = None

            return pd.DataFrame([res_dict])
        except Exception as e:
            print(f"❌ 未来涨幅计算异常 {symbol}: {e}")
            return None

    def fetch_individual_info(self, symbol: str):
        """获取个股基础基本面静态信息（总市值、流通市值等）"""
        query = f"""
            SELECT 
                `code`,
                `name`,
                `industry`, 
                ROUND(`mcap` / 1e8, 2) AS `mcap`, 
                ROUND(`ffmc` / 1e8, 2) AS `ffmc`
            FROM 
                {self.info_table} 
            WHERE 
                `code` = :code LIMIT 1
        """
        return self.query_to_df(query, {"code": symbol.zfill(6)})

    def fetch_dailys_data(self, symbol: str, start_date: str, end_date: str):
        """拉取个股指定时间段闭区间内的全量周期 K 线数据"""
        query = f"""
            SELECT 
                code,
                date,
                open, 
                high,
                low,
                close, 
                volume,
                amount,
                turnover_rate
            FROM 
                {self.kline_table}
            WHERE 
                code = :code
                AND date >= :start_date
                AND date <= :end_date
                AND adjust = :adjust
            ORDER BY date
        """

        params = {
            "code": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "adjust": self.adjust,
        }

        return self.query_to_df(query, params)

    def fetch_industry_data(self):
        """全市场多级申万行业映射基础数据获取"""
        query_industry = """
            SELECT
                stock_code,
                level1_name,
                level2_name,
                level3_name 
            FROM
                sw_stock_industry
        """
        return self.query_to_df(query_industry)

    def fetch_daily_lhb_data(self, list_date: str):
        """拉取某一指定日期上榜的龙虎榜去重统计明细（以市值最大降序作为主榜行）"""
        query = """
            SELECT
                code,
                interpretation,
                list_reason 
           FROM
                (
                    SELECT 
                        code,
                        interpretation,
                        list_reason,
                        ROW_NUMBER() OVER ( PARTITION BY code ORDER BY float_market_cap DESC ) AS rn
                    FROM lhb_detail
                    WHERE list_date = :list_date
                ) t
            WHERE
                t.rn = 1
        """
        return self.query_to_df(query, {"list_date": list_date})

    def fetch_cn_last_day_condition_codes(self, last_date: str):
        """依据注册表内的条件 SQL 表达式，筛选出上一周期/交易日契合初始选股标准的股票池"""
        condition = STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES")
        query = CONDITION_REGISTRY.get(condition)

        if query is None:
            print(f"❌ [未知] 条件码 {condition} 跳过前置过滤")
            return None
        print(f"🔍 [筛选] 上一日 {condition} 条件标的 ")

        return self.query_to_df(query, {"last_date": last_date})

    def fetch_resolve_trade_date(self, current_day: str) -> str:
        """根据当前扫描的时间锚点向前追溯，获取数据库中最新的前一周期/前一交易日的日期戳"""
        if STRATEGY_CONFIG.get("CN_USE_REAL_TIME_DATA", True):
            query = f"SELECT MAX(date) as latest_date FROM {self.kline_table}"
            result = self.query_to_df(query, {})
            return result["latest_date"].iloc[0].strftime("%Y-%m-%d")
        else:
            query = f"SELECT MAX(date) as prev_date FROM {self.kline_table} WHERE date < :current_day"
            result = self.query_to_df(query, {"current_day": current_day})
            return result["prev_date"].iloc[0].strftime("%Y-%m-%d")

    def close(self):
        self.engine.dispose()