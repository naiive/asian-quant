#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import math
import time
import random
import httpx
from io import BytesIO
import baostock as bs
import logging
import asyncio
import aiohttp
import traceback
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import numpy as np
import akshare as ak
from tqdm import tqdm
from sqlalchemy import create_engine, text

try:
    import conf.config as conf
except ImportError:
    class MockConf:
        DB_CONFIG = {
            "USER": "root",
            "PASS": "password",
            "HOST": "127.0.0.1",
            "PORT": 3306,
            "DB_NAME": "asian_quant"
        }

    conf = MockConf()

C_END, C_BOLD, C_RED, C_GREEN, C_YELLOW, C_BLUE, C_CYAN = "\033[0m", "\033[1m", "\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[36m"

TABLE_CONFIG = {
    "QUERY_DAILY_TABLE": "asian_quant_stock_daily",
    "INSERT_DAILY_TABLE": "asian_quant_stock_daily",
    "QUERY_STOCK_INFO": "asian_quant_stock_info",
    "SW_INDUSTRY_TABLE": "sw_stock_industry",
    "LHB_DETAIL_TABLE": "lhb_detail",
}

CONFIG = {
    # 数据周期：daily(日线), weekly(周线), monthly(月线)
    "PERIOD": "daily",

    # 【优先级最高】相对天数模式：0-今天, 1-昨天, 2-前天
    "LOOKBACK_DAYS": 0,

    # 固定日期模式
    # ***********************
    # LOOKBACK_DAYS 设置 None
    # ***********************
    "START_DATE": "20260820",
    "END_DATE": "20260820",
    # ***********************

    # 定向同步清单：若填入代码，则只同步这些，忽略过滤逻辑
    "TARGET_STOCKS": [],

    # 申万行业同步配置
    "SW_BATCH_SIZE": 500,   # 写库每批条数

    # 龙虎榜同步配置
    "LHB_START_DATE": "",   # 格式 YYYYMMDD，留空时使用 LOOKBACK_DAYS 逻辑
    "LHB_END_DATE": "",     # 格式 YYYYMMDD，留空时使用 LOOKBACK_DAYS 逻辑
    "LHB_BATCH_SIZE": 500,  # 写库每批条数

    # 并发与重试设置
    "MAX_WORKERS": 1,       # BaoStock 接口只能设置 1
    "MAX_RETRIES": 2,

    # 数据库表映射关系
    "TABLE_MAP": {
        "daily": "asian_quant_stock_daily",
        "weekly": "asian_quant_stock_weekly",
        "monthly": "asian_quant_stock_monthly",
        "basic_info": "asian_quant_stock_info",
        "sw_industry": "sw_stock_industry",
        "lhb_detail": "lhb_detail"
    },

    # 复权方式：qfq(前复权), hfq(后复权), None(不复权)
    "ADJUST": "qfq",

    # 过滤器配置
    "EXCLUDE_GEM": False,
    "EXCLUDE_KCB": True,
    "EXCLUDE_BJ": True,
    "EXCLUDE_ST": False,
    "EXCLUDE_DELIST": True
}

DB_CONFIG = conf.DB_CONFIG

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CURRENT_DATE_STR = datetime.now().strftime("%Y%m%d")
LOG_DIR = os.path.join(BASE_DIR, "data/logs", CURRENT_DATE_STR)
CACHE_DIR = os.path.join(BASE_DIR, "data/cache")
CN_STOCKS_CACHE = os.path.join(CACHE_DIR, "cn_stocks_cache.json")
US_CONTRACT_CACHE = os.path.join(CACHE_DIR, "us_contract_cache.json")
US_RWA_CACHE = os.path.join(CACHE_DIR, "us_rwa_cache.json")
US_STOCKS_CACHE = os.path.join(CACHE_DIR, "us_stocks_cache.json")
HK_STOCKS_CACHE = os.path.join(CACHE_DIR, "hk_stocks_cache.json")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


class ColoredFormatter(logging.Formatter):
    MAPPING = {
        logging.INFO: f"{C_BLUE}%(asctime)s [INFO]{C_END} %(message)s",
        logging.WARNING: f"{C_YELLOW}%(asctime)s [WARN]{C_END} %(message)s",
        logging.ERROR: f"{C_RED}%(asctime)s [ERROR]{C_END} %(message)s",
        logging.CRITICAL: f"{C_BOLD}{C_RED}%(asctime)s [CRIT]{C_END} %(message)s",
    }

    def format(self, record):
        fmt = self.MAPPING.get(record.levelno)
        return logging.Formatter(fmt, datefmt='%H:%M:%S').format(record)


class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg, file=sys.stdout)
            self.flush()
        except Exception(BaseException):
            self.handleError(record)


def setup_logger():
    lg = logging.getLogger('StockETL')
    lg.setLevel(logging.INFO)
    if lg.handlers:
        lg.handlers.clear()
    lg.propagate = False

    file_fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    fh = logging.FileHandler(os.path.join(LOG_DIR, "etl.log"), encoding='utf-8')
    fh.setFormatter(file_fmt)
    lg.addHandler(fh)

    th = TqdmLoggingHandler()
    th.setFormatter(ColoredFormatter())
    lg.addHandler(th)
    return lg


logger = setup_logger()


def get_engine():
    c = DB_CONFIG
    conn_url = (
        f"mysql+pymysql://{c['USER']}:{c['PASS']}@"
        f"{c['HOST']}:{c['PORT']}/{c['DB_NAME']}?charset=utf8mb4"
    )
    return create_engine(conn_url, pool_recycle=3600)


def apply_filters(df):
    before_count = len(df)

    if CONFIG.get("EXCLUDE_ST", True):
        df = df[~df['name'].str.contains(r'ST|\*ST', flags=re.IGNORECASE)]

    if CONFIG.get("EXCLUDE_DELIST", True):
        df = df[~df['name'].str.contains(r'退市|退')]

    df = df[~df['code'].str.startswith(('900', '200'))]

    if CONFIG.get("EXCLUDE_GEM", True):
        df = df[~df['code'].str.startswith(('300', '301'))]

    if CONFIG.get("EXCLUDE_KCB", True):
        df = df[~df['code'].str.startswith(('688', '689'))]

    if CONFIG.get("EXCLUDE_BJ", True):
        df = df[~df['code'].str.startswith(('8', '4', '9', '43', '83', '87'))]

    after_count = len(df)
    logger.info(
        f"🔍 {C_BOLD}{C_YELLOW}整体市场:{C_END} 总样本: {C_CYAN}{before_count}{C_END}支 | "
        f"剔除: {C_RED}{before_count - after_count}{C_END}支 | "
        f"有效: {C_GREEN}{after_count}{C_END}支"
    )
    return df


def get_stock_list_with_cache():
    today = datetime.now().strftime("%Y-%m-%d")

    if os.path.exists(CN_STOCKS_CACHE):
        try:
            with open(CN_STOCKS_CACHE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached.get("time") == today:
                    logger.info(f"{C_GREEN}✅ 缓存命中:{C_END} 使用今日代码清单")
                    return pd.DataFrame(cached['data'])
                else:
                    logger.info(f"{C_YELLOW}⚠️ 缓存过期:{C_END} 准备重新抓取")
        except Exception as e:
            logger.warning(f"{C_YELLOW}⚠️ 缓存解析失败:{C_END} {e}")

    logger.info("📡 接口更新: 抓取最新代码列表...")
    try:
        df = ak.stock_info_a_code_name()[["code", "name"]]
        df['code'] = df['code'].astype(str)
        with open(CN_STOCKS_CACHE, "w", encoding="utf-8") as f:
            json.dump({"time": today, "data": df.to_dict(orient="records")}, f, ensure_ascii=False, indent=2)
        return df
    except Exception as e:
        logger.error(f"{C_RED}❌ 股票清单接口调用失败:{C_END} {e}")
        return pd.DataFrame(columns=['code', 'name'])


def fetch_stock_data_baostock(item, s_date, e_date):
    raw_code = item['code']

    if raw_code.startswith(('60', '68', '90', '99')):
        bs_code = f"sh.{raw_code}"
    elif raw_code.startswith(('00', '30', '20')):
        bs_code = f"sz.{raw_code}"
    elif raw_code.startswith(('4', '8', '92')):
        bs_code = f"bj.{raw_code}"
    else:
        return {"code": raw_code, "df": None, "error": "未知市场"}

    def format_date(date_input):
        if not date_input:
            return ""
        s = str(date_input).replace("-", "").replace("/", "")
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        return date_input

    clean_s = format_date(s_date)
    clean_e = format_date(e_date)
    adj_map = {"qfq": "2", "hfq": "1", "none": "3", None: "3"}
    adj_param = adj_map.get(CONFIG.get("ADJUST"), "3")
    period = CONFIG.get("PERIOD", "daily")
    bs_freq = {"daily": "d", "weekly": "w", "monthly": "m"}.get(period, "d")

    base_fields = "date,open,high,low,close,volume,amount,pctChg,turn"
    fetch_fields = f"{base_fields},tradestatus" if period == "daily" else base_fields

    last_err = "未知错误"
    for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
        try:
            rs = bs.query_history_k_data_plus(
                code=bs_code,
                fields=fetch_fields,
                start_date=clean_s,
                end_date=clean_e,
                frequency=bs_freq,
                adjustflag=adj_param
            )

            if rs.error_code != '0':
                raise ValueError(f"BaoStock接口报错: {rs.error_msg}")

            data_list = []
            field_names = rs.fields
            while rs.next():
                row_data = rs.get_row_data()
                if period == "daily":
                    row_dict = dict(zip(field_names, row_data))
                    if row_dict.get('tradestatus') == '0':
                        continue
                data_list.append(row_data)

            if not data_list:
                return {"code": raw_code, "df": None, "error": "该时段无数据/停牌"}

            df = pd.DataFrame(data_list, columns=field_names)
            df['code'] = raw_code
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['adjust'] = CONFIG['ADJUST'] if CONFIG['ADJUST'] else 'none'

            num_cols = {"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume", "amount": "amount", "pctChg": "pct_chg", "turn": "turnover_rate"}
            df = df.rename(columns=num_cols)
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg', 'turnover_rate']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df['chg'] = np.where(
                100 + df['pct_chg'] != 0,
                (df['close'] * df['pct_chg'] / 100 + df['pct_chg']),
                0
            )
            df['chg'] = df['chg'].round(3)

            df['volume'] = df['volume'] / 100

            return {"code": raw_code, "df": df[['code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg', 'chg', 'turnover_rate', 'adjust']], "error": None}

        except Exception as e:
            last_err = str(e)
            time.sleep(1)
    return {"code": raw_code, "df": None, "error": last_err}


def mysql_upsert_logic(table, conn, keys, data_iter):
    data_list = [dict(zip(keys, row)) for row in data_iter]
    cols = ", ".join([f"`{k}`" for k in keys])
    plh = ", ".join([f":{k}" for k in keys])
    upd = ", ".join([f"`{k}`=VALUES(`{k}`)" for k in keys if k not in ['date', 'code', 'adjust']])
    sql = f"INSERT INTO {table.name} ({cols}) VALUES ({plh}) ON DUPLICATE KEY UPDATE {upd}"
    conn.execute(text(sql), data_list)


def fetch_stock_basic_info(item):
    code = item['code']
    time.sleep(random.uniform(0.1, 0.2))
    last_err = "未知错误"

    for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
        try:
            f_raw = ak.stock_individual_info_em(symbol=code)
            if f_raw is None or f_raw.empty:
                raise ValueError("基本信息为空")

            info_dict = dict(zip(f_raw['item'], f_raw['value']))

            def clean_numeric(val):
                if val in ["-", "None", "", "nan", None]:
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            data = {
                'code': code,
                'name': info_dict.get('股票简称'),
                'industry': info_dict.get('行业') if info_dict.get('行业') != "-" else "未知",
                'mcap': clean_numeric(info_dict.get('总市值')),
                'ffmc': clean_numeric(info_dict.get('流通市值')),
                'update_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            return {"code": code, "data": data, "error": None}

        except Exception as e:
            last_err = str(e)
            if attempt < CONFIG["MAX_RETRIES"]:
                time.sleep(0.5)

    return {"code": code, "data": None, "error": last_err}


def mysql_upsert_basic_info(table, conn, keys, data_iter):
    data_list = [dict(zip(keys, row)) for row in data_iter]
    if not data_list:
        return

    cols = ", ".join([f"`{k}`" for k in keys])
    plh = ", ".join([f":{k}" for k in keys])
    upd = ", ".join([f"`{k}`=VALUES(`{k}`)" for k in keys if k != 'code'])
    sql = f"INSERT INTO {table.name} ({cols}) VALUES ({plh}) ON DUPLICATE KEY UPDATE {upd}"

    conn.execute(text(sql), data_list)


def _sw_fetch_industry_data():
    logger.info("📡 拉取申万一级行业...")
    df1 = ak.sw_index_first_info()
    df1.columns = ["code", "name", "stock_count", "pe_static", "pe_ttm", "pb", "div_yield"]
    df1["code"] = df1["code"].str.replace(".SI", "", regex=False)

    logger.info("📡 拉取申万二级行业...")
    df2 = ak.sw_index_second_info()
    df2.columns = ["code", "name", "parent_name", "stock_count", "pe_static", "pe_ttm", "pb", "div_yield"]
    df2["code"] = df2["code"].str.replace(".SI", "", regex=False)

    logger.info("📡 拉取申万三级行业...")
    df3 = ak.sw_index_third_info()
    df3.columns = ["code", "name", "parent_name", "stock_count", "pe_static", "pe_ttm", "pb", "div_yield"]
    df3["code"] = df3["code"].str.replace(".SI", "", regex=False)

    return df1, df2, df3


def _sw_build_maps(df1, df2, df3):
    map1_by_name = {row["name"]: row for _, row in df1.iterrows()}
    map2_by_name = {row["name"]: row for _, row in df2.iterrows()}
    map3_by_lv2_name = {}

    for _, row in df3.iterrows():
        map3_by_lv2_name.setdefault(row["parent_name"], []).append(row)

    return map1_by_name, map2_by_name, map3_by_lv2_name


def _sw_fetch_level3_cons(code3):
    for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
        try:
            time.sleep(random.uniform(0.3, 0.8))
            cons = ak.sw_index_third_cons(symbol=code3 + ".SI")
            if cons is not None and not cons.empty:
                return cons
            return None
        except ValueError:
            return None
        except (ConnectionError, OSError) as e:
            logger.warning(f"  ⚠️ 网络异常 [{attempt}/{CONFIG['MAX_RETRIES']}] {code3}: {e}")
            if attempt < CONFIG["MAX_RETRIES"]:
                time.sleep(random.uniform(2, 5))
    return None


def _sw_fetch_level2_cons(code2):
    try:
        cons = ak.sw_index_third_cons(symbol=code2 + ".SI")
        if cons is not None and not cons.empty:
            return cons
    except (ValueError, KeyError, AttributeError):
        pass
    return None


def _sw_build_record(stock_code, stock_name, lv1, lv2, row3, updated_at):
    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "level1_code": lv1["code"],
        "level1_name": lv1["name"],
        "level1_stock_count": lv1["stock_count"],
        "level1_pe_static": lv1["pe_static"],
        "level1_pe_ttm": lv1["pe_ttm"],
        "level1_pb": lv1["pb"],
        "level1_div_yield": lv1["div_yield"],
        "level2_code": lv2["code"],
        "level2_name": lv2["name"],
        "level2_parent_name": lv2["parent_name"],
        "level2_stock_count": lv2["stock_count"],
        "level2_pe_static": lv2["pe_static"],
        "level2_pe_ttm": lv2["pe_ttm"],
        "level2_pb": lv2["pb"],
        "level2_div_yield": lv2["div_yield"],
        "level3_code": row3["code"] if row3 is not None else None,
        "level3_name": row3["name"] if row3 is not None else None,
        "level3_parent_name": row3["parent_name"] if row3 is not None else None,
        "level3_stock_count": row3["stock_count"] if row3 is not None else None,
        "level3_pe_static": row3["pe_static"] if row3 is not None else None,
        "level3_pe_ttm": row3["pe_ttm"] if row3 is not None else None,
        "level3_pb": row3["pb"] if row3 is not None else None,
        "level3_div_yield": row3["div_yield"] if row3 is not None else None,
        "updated_at": updated_at,
    }


def _sw_clean_record(record):
    return {
        k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
        for k, v in record.items()
    }


def _sw_batch_upsert(engine, records):
    records = [_sw_clean_record(r) for r in records]

    upsert_sql = text("""
    INSERT INTO sw_stock_industry (
        stock_code, stock_name,
        level1_code, level1_name, level1_stock_count, level1_pe_static, level1_pe_ttm, level1_pb, level1_div_yield,
        level2_code, level2_name, level2_parent_name, level2_stock_count, level2_pe_static, level2_pe_ttm, level2_pb, level2_div_yield,
        level3_code, level3_name, level3_parent_name, level3_stock_count, level3_pe_static, level3_pe_ttm, level3_pb, level3_div_yield,
        updated_at
    ) VALUES (
        :stock_code, :stock_name,
        :level1_code, :level1_name, :level1_stock_count, :level1_pe_static, :level1_pe_ttm, :level1_pb, :level1_div_yield,
        :level2_code, :level2_name, :level2_parent_name, :level2_stock_count, :level2_pe_static, :level2_pe_ttm, :level2_pb, :level2_div_yield,
        :level3_code, :level3_name, :level3_parent_name, :level3_stock_count, :level3_pe_static, :level3_pe_ttm, :level3_pb, :level3_div_yield,
        :updated_at
    )
    ON DUPLICATE KEY UPDATE
        stock_name=VALUES(stock_name),
        level1_code=VALUES(level1_code), level1_name=VALUES(level1_name), level1_stock_count=VALUES(level1_stock_count),
        level1_pe_static=VALUES(level1_pe_static), level1_pe_ttm=VALUES(level1_pe_ttm), level1_pb=VALUES(level1_pb), level1_div_yield=VALUES(level1_div_yield),
        level2_code=VALUES(level2_code), level2_name=VALUES(level2_name), level2_parent_name=VALUES(level2_parent_name), level2_stock_count=VALUES(level2_stock_count),
        level2_pe_static=VALUES(level2_pe_static), level2_pe_ttm=VALUES(level2_pe_ttm), level2_pb=VALUES(level2_pb), level2_div_yield=VALUES(level2_div_yield),
        level3_code=VALUES(level3_code), level3_name=VALUES(level3_name), level3_parent_name=VALUES(level3_parent_name), level3_stock_count=VALUES(level3_stock_count),
        level3_pe_static=VALUES(level3_pe_static), level3_pe_ttm=VALUES(level3_pe_ttm), level3_pb=VALUES(level3_pb), level3_div_yield=VALUES(level3_div_yield),
        updated_at=VALUES(updated_at)
    """)

    batch_size = CONFIG.get("SW_BATCH_SIZE", 500)
    total = 0
    with engine.begin() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            conn.execute(upsert_sql, batch)
            total += len(batch)
            logger.info(f"  💾 已写入 {C_GREEN}{total}{C_END} / {len(records)} 条")

    logger.info(f"{C_GREEN}✅ 申万行业写库完成，共 {total} 条{C_END}")


def sync_sw_industry():
    logger.info(f"{C_BOLD}📊 开始同步申万行业三级分类...{C_END}")
    engine = get_engine()
    try:
        df1, df2, df3 = _sw_fetch_industry_data()
        map1_by_name, map2_by_name, _ = _sw_build_maps(df1, df2, df3)

        now = datetime.now()
        stock_map = {}

        pbar = tqdm(
            df3.iterrows(),
            total=len(df3),
            desc=f"{C_BOLD}🏭 三级行业{C_END}",
            bar_format="{l_bar}%s{bar:25}%s{r_bar}" % (C_CYAN, C_END),
            dynamic_ncols=True
        )
        for _, row3 in pbar:
            time.sleep(random.uniform(0.3, 0.8))
            code3 = row3["code"]
            name3 = row3["name"]
            parent_name3 = row3["parent_name"]

            lv2 = map2_by_name.get(parent_name3)
            if lv2 is None:
                logger.warning(f"三级 {name3} 找不到二级: {parent_name3}")
                continue

            lv1 = map1_by_name.get(lv2["parent_name"])
            if lv1 is None:
                logger.warning(f"二级 {lv2['name']} 找不到一级: {lv2['parent_name']}")
                continue

            cons = _sw_fetch_level3_cons(code3)
            if cons is None:
                pbar.set_postfix({"状态": f"{name3} 无数据"})
                continue

            for _, stock in cons.iterrows():
                stock_code = str(stock["股票代码"]).split(".")[0]
                stock_map[stock_code] = _sw_build_record(
                    stock_code, stock["股票简称"], lv1, lv2, row3, now
                )
            pbar.set_postfix({"最新": name3, "已收录": len(stock_map)})

        logger.info(f"{C_BOLD}💾 写库，共 {C_GREEN}{len(stock_map)}{C_END}{C_BOLD} 条记录{C_END}")
        _sw_batch_upsert(engine, list(stock_map.values()))

    except (ValueError, KeyError, AttributeError, ConnectionError, OSError) as e:
        logger.critical(f"🛑 申万行业同步失败: {e}\n{traceback.format_exc()}")
    finally:
        engine.dispose()


def _lhb_last_trading_day(ref_dt: datetime) -> datetime:
    dt = ref_dt
    while dt.weekday() >= 5:
        dt -= timedelta(days=1)
    return dt


def _lhb_resolve_dates():
    s = CONFIG.get("LHB_START_DATE", "").strip()
    e = CONFIG.get("LHB_END_DATE", "").strip()
    if s and e:
        return s, e

    start_str = CONFIG["START_DATE"]
    end_str = CONFIG["END_DATE"]

    today_str = datetime.now().strftime("%Y%m%d")
    if start_str == today_str:
        last_td = _lhb_last_trading_day(datetime.now())
        start_str = last_td.strftime("%Y%m%d")
        end_str = start_str
        logger.info(
            f"📅 今日({today_str})龙虎榜未发布，自动回退至最近工作日: "
            f"{C_CYAN}{start_str}{C_END}"
        )

    return start_str, end_str


def _lhb_clean_float(val):
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, str) and val.strip() in ("-", "", "nan", "None"):
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (ValueError, TypeError):
        return None


def _lhb_transform(raw_df):
    col_map = {
        "代码": "code",
        "名称": "name",
        "上榜日": "list_date",
        "解读": "interpretation",
        "收盘价": "close",
        "涨跌幅": "pct_chg",
        "龙虎榜净买额": "lhb_net_buy",
        "龙虎榜买入额": "lhb_buy",
        "龙虎榜卖出额": "lhb_sell",
        "龙虎榜成交额": "lhb_amount",
        "市场总成交额": "market_amount",
        "净买额占总成交比": "net_buy_ratio",
        "成交额占总成交比": "amount_ratio",
        "换手率": "turnover_rate",
        "流通市值": "float_market_cap",
        "上榜原因": "list_reason",
        "上榜后1日": "after_1d",
        "上榜后2日": "after_2d",
        "上榜后5日": "after_5d",
        "上榜后10日": "after_10d",
    }

    df = raw_df.rename(columns=col_map)

    target_cols = list(col_map.values())

    df = df[[c for c in target_cols if c in df.columns]]

    df["list_date"] = pd.to_datetime(df["list_date"], errors="coerce").dt.date

    num_cols = [
        "close", "pct_chg",
        "lhb_net_buy", "lhb_buy", "lhb_sell", "lhb_amount",
        "market_amount", "net_buy_ratio", "amount_ratio",
        "turnover_rate", "float_market_cap",
        "after_1d", "after_2d", "after_5d", "after_10d",
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].apply(_lhb_clean_float)

    amount_cols = ["lhb_net_buy", "lhb_buy", "lhb_sell", "lhb_amount", "market_amount"]
    for col in amount_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 10_000

    if "float_market_cap" in df.columns:
        df["float_market_cap"] = pd.to_numeric(df["float_market_cap"], errors="coerce") / 1e8

    for col in amount_cols:
        if col in df.columns:
            df[col] = df[col].round(2)
    if "float_market_cap" in df.columns:
        df["float_market_cap"] = df["float_market_cap"].round(4)

    for col in ["code", "name", "interpretation", "list_reason"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    df["list_reason"] = df["list_reason"].replace("", "未知原因")

    df["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return df.to_dict(orient="records")


def _lhb_clean_record(record):
    cleaned = {}
    for k, v in record.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def _lhb_batch_upsert(engine, records):
    if not records:
        logger.warning(f"{C_YELLOW}⚠️ 龙虎榜无有效数据，跳过写库{C_END}")
        return

    records = [_lhb_clean_record(r) for r in records]

    keys = list(records[0].keys())
    cols = ", ".join([f"`{k}`" for k in keys])
    plh = ", ".join([f":{k}" for k in keys])

    skip_upd = {"code", "list_date", "list_reason"}
    upd = ", ".join([f"`{k}`=VALUES(`{k}`)" for k in keys if k not in skip_upd])

    sql = text(
        f"INSERT INTO lhb_detail ({cols}) VALUES ({plh}) "
        f"ON DUPLICATE KEY UPDATE {upd}"
    )

    batch_size = CONFIG.get("LHB_BATCH_SIZE", 500)
    total = 0
    with engine.begin() as conn:
        for i in range(0, len(records), batch_size):
            batch = records[i: i + batch_size]
            conn.execute(sql, batch)
            total += len(batch)
            logger.info(f"  💾 龙虎榜已写入 {C_GREEN}{total}{C_END} / {len(records)} 条")

    logger.info(f"{C_GREEN}✅ 龙虎榜写库完成，共 {total} 条{C_END}")


def sync_lhb_detail():
    logger.info(f"{C_BOLD}📋 开始同步龙虎榜详情...{C_END}")
    engine = get_engine()

    try:
        start_str, end_str = _lhb_resolve_dates()

        start_dt = datetime.strptime(start_str, "%Y%m%d")
        end_dt = datetime.strptime(end_str, "%Y%m%d")

        date_range = []
        cur = start_dt
        while cur <= end_dt:
            date_range.append(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)

        logger.info(
            f"📅 同步区间: {C_CYAN}{start_str}{C_END} → {C_CYAN}{end_str}{C_END} "
            f"({C_YELLOW}{len(date_range)}{C_END} 个自然日)"
        )

        all_records = []

        pbar = tqdm(
            date_range,
            desc=f"{C_BOLD}📋 龙虎榜进度{C_END}",
            bar_format="{l_bar}%s{bar:25}%s{r_bar}" % (C_YELLOW, C_END),
            dynamic_ncols=True
        )

        for date_str in pbar:
            pbar.set_postfix({"日期": date_str, "已收": len(all_records)})

            for attempt in range(1, CONFIG["MAX_RETRIES"] + 1):
                try:
                    raw = ak.stock_lhb_detail_em(
                        start_date=date_str,
                        end_date=date_str
                    )
                    if raw is None or raw.empty:
                        logger.info(f"  ⏭️ {date_str}: 非交易日或暂无龙虎榜数据，跳过")
                        break

                    records = _lhb_transform(raw)
                    all_records.extend(records)
                    logger.info(
                        f"  📥 {date_str}: 获取 {C_GREEN}{len(records)}{C_END} 条"
                    )
                    break

                except TypeError as e:
                    logger.info(f"  ⏭️ {date_str}: 接口无数据（{e}），视为非交易日跳过")
                    break

                except Exception as e:
                    logger.warning(
                        f"  ⚠️ [{attempt}/{CONFIG['MAX_RETRIES']}] {date_str} 拉取失败: {e}"
                    )
                    if attempt < CONFIG["MAX_RETRIES"]:
                        time.sleep(random.uniform(1, 3))

        logger.info(
            f"{C_BOLD}💾 写库，共 {C_GREEN}{len(all_records)}{C_END}{C_BOLD} 条龙虎榜记录{C_END}"
        )
        _lhb_batch_upsert(engine, all_records)

    except Exception as e:
        logger.critical(f"🛑 龙虎榜同步失败: {e}\n{traceback.format_exc()}")
    finally:
        engine.dispose()


async def start_hist_engine(todo_jobs, total_query, _already_exist):
    sem = asyncio.Semaphore(CONFIG["MAX_WORKERS"])
    loop = asyncio.get_running_loop()
    success_dfs, failed_logs = [], []

    async def worker(item):
        async with sem:
            with ThreadPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool, fetch_stock_data_baostock, item, CONFIG["START_DATE"], CONFIG["END_DATE"]
                )

    pbar = tqdm(
        total=total_query,
        desc=f"{C_BOLD}📊 [{CONFIG['PERIOD']}] 同步进度{C_END}",
        bar_format="{l_bar}%s{bar:25}%s{r_bar}" % (C_GREEN, C_END),
        dynamic_ncols=True
    )

    tasks = [worker(it) for it in todo_jobs]
    for future in asyncio.as_completed(tasks):
        res = await future
        if res["df"] is not None:
            success_dfs.append(res["df"])
        else:
            failed_logs.append(res)
        pbar.update(1)
        pbar.set_postfix({"✅成功": len(success_dfs), "❌失败": len(failed_logs)})
    pbar.close()

    if failed_logs:
        logger.error(f"\n{C_RED}❌ 以下股票行情同步失败 ({len(failed_logs)}支):{C_END}")
        for err in failed_logs:
            print(f"代码: {C_YELLOW}{err['code']}{C_END} | 原因: {err['error']}")
        print("-" * 30)

    if success_dfs:
        target = CONFIG["TABLE_MAP"].get(CONFIG["PERIOD"])
        logger.info(f"{C_GREEN}💾 正在批量更新/入库数据库...{C_END}")
        pd.concat(success_dfs).to_sql(
            name=target,
            con=get_engine(),
            if_exists='append',
            index=False,
            method=mysql_upsert_logic
        )


async def start_basic_info_engine(todo_jobs):
    sem = asyncio.Semaphore(CONFIG["MAX_WORKERS"])
    loop = asyncio.get_running_loop()
    success_data, failed_logs = [], []

    async def worker(item):
        async with sem:
            with ThreadPoolExecutor() as pool:
                return await loop.run_in_executor(pool, fetch_stock_basic_info, item)

    pbar = tqdm(
        total=len(todo_jobs),
        desc=f"{C_BOLD}📋 基本信息进度{C_END}",
        bar_format="{l_bar}%s{bar:25}%s{r_bar}" % (C_CYAN, C_END),
        dynamic_ncols=True
    )

    tasks = [worker(it) for it in todo_jobs]
    for future in asyncio.as_completed(tasks):
        res = await future
        if res["data"] is not None:
            success_data.append(res["data"])
        else:
            failed_logs.append(res)
        pbar.update(1)
    pbar.close()

    if failed_logs:
        logger.error(f"\n{C_RED}❌ 以下股票基本信息抓取失败 ({len(failed_logs)}支):{C_END}")
        for err in failed_logs:
            print(f"代码: {C_YELLOW}{err['code']}{C_END} | 原因: {err['error']}")
        print("-" * 30)

    if success_data:
        target = CONFIG["TABLE_MAP"].get["basic_info"]
        logger.info(f"{C_GREEN}💾 正在更新市值/行业信息...{C_END}")
        pd.DataFrame(success_data).to_sql(
            name=target,
            con=get_engine(),
            if_exists='append',
            index=False,
            method=mysql_upsert_basic_info
        )

BITGET_API = "https://api.bitget.com/api/v3/market/instruments?category=USDT-FUTURES"
SINA_API = "https://hq.sinajs.cn/list=gb_{}"
ONDO_API = "https://app.ondo.finance/api/v2/assets"

FINNHUB_TOKEN = conf.FINNHUB_CONFIG.get("TOKEN")
FINNHUB_SYMBOLS_API = f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={FINNHUB_TOKEN}"

MAJOR_MIC = {'XNYS', 'XASE', 'BATS', 'ARCX', 'XNMS', 'XNCM', 'XNGS', 'IEXG', 'XNAS'}

MIC_NAME = {
    'XNYS': '纽交所',
    'XASE': 'NYSE American',
    'BATS': 'CBOE BZX',
    'ARCX': 'NYSE Arca',
    'XNMS': '纳斯达克全球精选',
    'XNCM': '纳斯达克资本市场',
    'XNGS': '纳斯达克全球市场',
    'IEXG': 'IEX',
    'XNAS': '纳斯达克',
}

TYPE_NAME = {
    'Common Stock': '普通股',
    'ADR': '美国存托凭证',
    'ETP': 'ETF/ETP基金',
    'REIT': '房地产信托',
}

async def get_sina_chinese_name(session, code):
    sina_code = code.lower().replace(".", "-")
    url = SINA_API.format(sina_code)
    headers = {
        "Referer": "https://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)"
    }
    try:
        async with session.get(url, headers=headers, timeout=5) as resp:
            texts = await resp.text(encoding='gbk')
            match = re.search(r'"(.*?)"', texts)
            if match:
                parts = match.group(1).split(',')
                if len(parts) > 1:
                    return parts[0]
    except Exception as e:
        print(e)
    return code


async def process_contract_stocks(session):
    print("🚀 开始抓取美股合约数据...")
    async with session.get(BITGET_API) as resp:
        bg_data = await resp.json()
        bitget_codes = [i['baseCoin'] for i in bg_data['data'] if i.get('symbolType') == 'stock']

    print(f"🔍 正在匹配 {len(bitget_codes)} 个标的的中文信息...")
    tasks = [get_sina_chinese_name(session, code) for code in bitget_codes]
    names = await asyncio.gather(*tasks)

    final_data = [{"code": code, "name": name} for code, name in zip(bitget_codes, names)]

    with open(US_CONTRACT_CACHE, "w", encoding="utf-8") as f:
        json.dump({"data": final_data}, f, indent=4, ensure_ascii=False)
    print("✅ us_contract_cache.json 自动映射完成！")


async def process_ondo_assets(session):
    print("🚀 开始抓取美股RWA数据...")
    try:
        async with session.get(ONDO_API) as resp:
            assets_dict = await resp.json()
            result_list = [
                {"code": item["ticker"], "name": item["assetName"]}
                for item in assets_dict.get("assets", [])
                if item.get("ticker") is not None
            ]

            with open(US_RWA_CACHE, "w", encoding="utf-8") as f:
                json.dump({"data": result_list}, f, indent=4, ensure_ascii=False)
            print("✅ ondo_assets_cache.json 抓取完成！")
    except Exception as e:
        print(f"❌ Ondo 抓取失败: {e}")


async def process_all_stocks(session):
    print("🚀 开始抓取美股股票数据...")
    try:
        async with session.get(FINNHUB_SYMBOLS_API) as resp:
            symbols = await resp.json()

            result_list = [
                {
                    "code": item["symbol"],
                    "name": item["description"],
                    "mic": f"{item['mic']} {MIC_NAME.get(item['mic'], '')}".strip(),
                    "type": f"{item['type']} {TYPE_NAME.get(item['type'], item['type'])}".strip(),
                }
                for item in symbols
                if item.get("mic") in MAJOR_MIC
                and item.get("type") in TYPE_NAME
            ]

            with open(US_STOCKS_CACHE, "w", encoding="utf-8") as f:
                json.dump({"data": result_list}, f, indent=4, ensure_ascii=False)
            print(f"✅ us_stocks_cache.json 抓取完成！共 {len(result_list)} 条")
    except Exception as e:
        print(f"❌ 美股抓取失败: {e}")


async def us_stock_cache():
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            process_contract_stocks(session),
            process_ondo_assets(session),
            process_all_stocks(session)
        )

VALID_CATEGORIES = {
    'Equity': '股票',
    'Exchange Traded Products': '交易型产品',
    'Derivative Warrants': '衍生权证(窝轮)',
    'Callable Bull/Bear Contracts': '牛熊证',
    'Real Estate Investment Trusts': '房地产信托REITs'
}

SUB_CATEGORY_NAME = {
    'Equity Securities (Main Board)': '主板股票',
    'Equity Securities (GEM)': '创业板股票',
    'Exchange Traded Funds': 'ETF基金',
    'Leveraged and Inverse': '杠杆及反向产品',
}

async def process_hk_stocks():
    print("🚀 开始抓取港股数据...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(conf.HKEX_URL)
            resp.raise_for_status()

        df = pd.read_excel(BytesIO(resp.content), skiprows=2)
        df.columns = df.columns.str.strip()

        df = df.dropna(subset=['Stock Code', 'Name of Securities'])
        df['Stock Code'] = df['Stock Code'].astype(str).str.strip()

        df = df[df['Category'].isin(VALID_CATEGORIES.keys())].copy()

        df['Sub-Category'] = df['Sub-Category'].fillna('').str.strip()

        def get_type_label(row):
            cat = row['Category']
            sub_cat = row['Sub-Category']

            cat_cn = VALID_CATEGORIES.get(cat, cat)

            if not sub_cat:
                return f"{cat} {cat_cn}".strip()

            sub_cn = SUB_CATEGORY_NAME.get(sub_cat, '')
            return f"{sub_cat} {sub_cn}".strip() if sub_cn else sub_cat

        result_list = [
            {
                "code": row['Stock Code'].zfill(5),
                "name": str(row['Name of Securities']).strip(),
                "type": VALID_CATEGORIES.get(row['Category']),
                "sub_type": get_type_label(row)
            }
            for _, row in df.iterrows()
        ]

        with open(HK_STOCKS_CACHE, "w", encoding="utf-8") as f:
            json.dump({"data": result_list}, f, indent=4, ensure_ascii=False)

        print(f"✅ hk_stocks_cache.json 抓取完成！共 {len(result_list)} 条品种")

    except httpx.HTTPStatusError as e:
        print(f"❌ 网络请求失败，状态码: {e.response.status_code}")
    except Exception as e:
        print(f"❌ 港股解析或保存失败: {e}")

def main():
    start_ts = time.time()
    logger.info(f"{C_BOLD}Asian Quant ETL 同步系统 (全量更新模式){C_END}")

    print(f"{C_BOLD}任务类型选择：{C_END}")
    print(f"1. {C_GREEN}同步/更新行情 ({CONFIG['PERIOD']}){C_END}")
    print(f"2. {C_CYAN}同步/更新基本信息{C_END}")
    print(f"3. {C_YELLOW}同步/更新申万行业三级分类{C_END}")
    print(f"4. {C_BLUE}同步/更新龙虎榜详情{C_END}")
    print(f"5. {C_BLUE}同步/美股标的（全市场/合约/RWA）缓存{C_END}")
    print(f"6. {C_BLUE}同步/港股标的缓存{C_END}")
    choice = input("\n请输入数字 (1 / 2 / 3 / 4 / 5 / 6): ").strip()

    if choice == '5':
        asyncio.run(us_stock_cache())
        return

    if choice == '6':
        asyncio.run(process_hk_stocks())
        return

    if choice == '3':
        sync_sw_industry()
        logger.info(f"{C_BOLD}🏁 任务完成! 总耗时: {time.time() - start_ts:.2f}s{C_END}")
        return

    if choice == '4':
        lookback = CONFIG.get("LOOKBACK_DAYS")
        if lookback is not None and not (
            CONFIG.get("LHB_START_DATE") and CONFIG.get("LHB_END_DATE")
        ):
            today_dt = datetime.now()
            if lookback == 0:
                start_dt = end_dt = today_dt
            else:
                yesterday_dt = today_dt - timedelta(days=1)
                start_dt = yesterday_dt - timedelta(days=int(lookback) - 1)
                end_dt = yesterday_dt
            CONFIG["START_DATE"] = start_dt.strftime("%Y%m%d")
            CONFIG["END_DATE"] = end_dt.strftime("%Y%m%d")

        sync_lhb_detail()
        logger.info(f"{C_BOLD}🏁 任务完成! 总耗时: {time.time() - start_ts:.2f}s{C_END}")
        return

    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"❌ BaoStock 登录失败: {lg.error_msg}")
        return

    lookback = CONFIG.get("LOOKBACK_DAYS")
    if lookback is not None:
        today_dt = datetime.now()
        if lookback == 0:
            start_dt = end_dt = today_dt
        else:
            yesterday_dt = today_dt - timedelta(days=1)
            start_dt = yesterday_dt - timedelta(days=int(lookback) - 1)
            end_dt = yesterday_dt
        CONFIG["START_DATE"] = start_dt.strftime("%Y%m%d")
        CONFIG["END_DATE"] = end_dt.strftime("%Y%m%d")

    try:
        df_all = get_stock_list_with_cache()
        if df_all.empty:
            return

        if choice == '1':
            logger.info("📡 启动行情抓取任务...")
            todo_hist = (
                apply_filters(df_all).to_dict(orient="records")
                if not CONFIG["TARGET_STOCKS"]
                else [{"code": str(c)} for c in CONFIG["TARGET_STOCKS"]]
            )
            asyncio.run(start_hist_engine(todo_hist, len(todo_hist), 0))

        elif choice == '2':
            logger.info("📡 启动基本信息抓取任务...")
            todo_basic = (
                df_all.to_dict(orient="records")
                if not CONFIG["TARGET_STOCKS"]
                else [{"code": str(c)} for c in CONFIG["TARGET_STOCKS"]]
            )
            asyncio.run(start_basic_info_engine(todo_basic))

    except Exception as e:
        logger.critical(f"🛑 程序崩溃: {e}\n{traceback.format_exc()}")
    finally:
        bs.logout()
        logger.info("📡 BaoStock 安全离线")

    logger.info(f"{C_BOLD}🏁 任务完成! 总耗时: {time.time() - start_ts:.2f}s{C_END}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{C_YELLOW}👋 检测到手动中断，系统安全离线{C_END}")
        try:
            bs.logout()
        except Exception(IOError):
            pass
        sys.exit(0)