#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gc
import time
from functools import partial
import pandas as pd

from conf.config import STRATEGY_CONFIG, SYSTEM_CONFIG
from conf.registry import STRATEGY_REGISTRY
from core.asyncs.dispatcher import run_dispatch
from core.dat.enrich import enrich_future_changes, enrich_results_v2, upsert_results_to_mysql
from core.dat.handler import DataHandler
from core.notify import csv_exporter, email_sender, telegram_sender

_sub_process_handler = None
_G_REALTIME_CACHE = None

def _standalone_strategy_worker(symbol, run_date, run_names, realtime_data=None, lhb_data=None, industry_data=None):
    global _sub_process_handler
    if _sub_process_handler is None:
        _sub_process_handler = DataHandler()

    if realtime_data is not None:
        _sub_process_handler.realtime_cache = realtime_data

    if lhb_data is not None:
        _sub_process_handler.mysql_client.lhb_cache = lhb_data

    if industry_data is not None:
        _sub_process_handler.mysql_client.industry_cache = industry_data

    target_df = _sub_process_handler.get_full_data(symbol, run_date)

    if target_df.empty:
        return None

    day_hits = {}
    for name in run_names:
        run_func = STRATEGY_REGISTRY.get(name)
        if run_func:
            res = run_func(target_df, symbol)
            if res:
                day_hits[name] = res

    return day_hits if day_hits else None

class MarketScanner:

    def __init__(self):
        self.handler = DataHandler()
        self.matched_list = []

    async def run_full_scan(self, symbols=None):
        """[主逻辑] 遍历交易周期 -> 动态池构建 -> 核心并行扫描 -> 销毁释放 -> 管道导出"""
        run_names = STRATEGY_CONFIG.get("CN_RUN_STRATEGIES")
        if not run_names:
            raise ValueError("❌ [错误] 未配置 CN_RUN_STRATEGIES")

        valid_strategies = set(STRATEGY_REGISTRY.keys())
        invalid_names = [
            name for name in run_names if name not in valid_strategies
        ]

        if invalid_names:
            raise ValueError(
                f"\n❌ [错误] 配置的策略名称不存在\n"
                f"   [无效] {invalid_names}\n"
                f"   [有效] {sorted(valid_strategies)}"
            )

        print(f"🎯 [策略] {' '.join(run_names)}")

        all_trade_days = self.handler.mysql_client.get_trade_days_list()

        if not all_trade_days:
            print("❌ [错误] 未找到符合条件的交易日/周期")
            return

        current_interval = STRATEGY_CONFIG.get("CN_INTERVAL", "daily")
        print(f"📅 [周期] 当前运行模式: {current_interval} | 共计 {len(all_trade_days)} 个结算节点")

        base_symbols = symbols or self.handler.get_target_list()

        print("🌐 [加载] 全市场多级行业数据")
        global_industry_dict = (
            self.handler.mysql_client.fetch_industry_data()
            .set_index("stock_code")
            .to_dict("index")
        )

        for current_day in all_trade_days:
            day_start = time.time()

            target_symbols = base_symbols

            if current_interval == "daily":
                day_lhb_dict = (
                    self.handler.mysql_client.fetch_daily_lhb_data(
                        list_date=current_day
                    )
                    .set_index("code")
                    .to_dict("index")
                )
            else:
                day_lhb_dict = {}

            if STRATEGY_CONFIG.get("CN_LAST_DAY_CONDITION_CODES") and len(STRATEGY_CONFIG.get("CN_TEST_CODE")) == 0:
                last_day = self.handler.mysql_client.fetch_resolve_trade_date(current_day)

                if not last_day:
                    print(f"⚠️ [跳过] {current_day} 无法解析上一周期的锚点日期，跳过该节点")
                    continue

                codes = self.handler.mysql_client.fetch_cn_last_day_condition_codes(last_date=last_day)

                if codes is not None and not codes.empty:
                    target_symbols = codes["code"].drop_duplicates().tolist()
                else:
                    print(f"🏁 [结束] {current_day} 由于上一周期满足过滤条件的标的池为空，直接略过")
                    continue

            if STRATEGY_CONFIG.get("CN_USE_REAL_TIME_DATA", True):
                self.handler.prepare_realtime_data()

            worker_proxy = partial(
                _standalone_strategy_worker,
                run_date=current_day,
                run_names=run_names,
                realtime_data=self.handler.realtime_cache,
                lhb_data=day_lhb_dict,
                industry_data=global_industry_dict,
            )

            day_results = await run_dispatch(
                symbols=target_symbols,
                worker_func=worker_proxy,
                desc=f"[{current_interval.upper()} 扫描] {current_day}",
            )

            if day_results:
                total_signals = sum(len(res) for res in day_results)
                if current_interval == "daily":
                    print(f"📡 [加载] {current_day} 龙虎榜数据完成")
                print(f"✅ [信号] {current_day} 命中 {total_signals} 条")
                self.export_results(day_results)
                print(f"⏱️ [完成] 耗时 {time.time() - day_start:.2f}s 时间 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
            else:
                print(f"🚫 [未存] {current_day} 扫描结束")

            gc.collect()

        print(f"\n🏁 [结束] 累计处理 {len(all_trade_days)} 个周期节点")

    def export_results(self, results: list = None):
        """中间件管道式结果归档与分发"""
        target_list = results if results is not None else self.matched_list
        if not target_list:
            return

        buckets = {}
        for bundle in target_list:
            for strategy_name, strategy_data in bundle.items():
                if strategy_name not in buckets:
                    buckets[strategy_name] = []
                buckets[strategy_name].append(strategy_data)

        for strategy_name, strategy_data in buckets.items():
            print(f"📊 [处理] 策略 {strategy_name} {len(strategy_data)} 条")

            flattened_data = []
            for item in strategy_data:
                if isinstance(item, list):
                    flattened_data.extend(item)
                else:
                    flattened_data.append(item)

            strategy_df = pd.DataFrame(flattened_data)

            if SYSTEM_CONFIG.get("ENABLE_RESULT_ENRICHMENT", False):
                strategy_df = enrich_results_v2(strategy_df, handler=self.handler)

            if SYSTEM_CONFIG.get("ENABLE_RESULT_FUTURE", False):
                strategy_df = enrich_future_changes(strategy_df, handler=self.handler, days_list=SYSTEM_CONFIG.get("FUTURE_DAYS_LIST", [1, 2, 3]))

            if SYSTEM_CONFIG.get("ENABLE_RESULT_MYSQL", False):
                strategy_df = upsert_results_to_mysql(strategy_df, strategy_name=strategy_name, handler=self.handler)

            if SYSTEM_CONFIG.get("ENABLE_EXPORT", False):
                csv_exporter.csv_exporter(strategy_df, strategy_name=strategy_name)

            if SYSTEM_CONFIG.get("ENABLE_EMAIL", False):
                email_sender.email_sender(strategy_df, strategy_name=strategy_name)

            if SYSTEM_CONFIG.get("ENABLE_TELEGRAM", False):
                telegram_sender.telegram_sender(strategy_df, strategy_name=strategy_name)