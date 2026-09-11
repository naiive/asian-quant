#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import random
from core.util.decorator import timer
from engine.cn_engine import MarketScanner
from core.dat.manager import StockListManager
from core.client.mysql import MySQLClient
from core.util.logger import LogRedirector
from conf.config import SYSTEM_CONFIG, PATH_CONFIG, STRATEGY_CONFIG

async def start_app():
    db = MySQLClient()
    manager = StockListManager(db)

    symbols_df = manager.get_stock_list()
    if symbols_df is None or symbols_df.empty:
        print("❌ [错误] 无法从数据库获取股票列表，请检查网络或数据库配置")
        return

    all_codes = symbols_df['code'].tolist()
    sample_size = SYSTEM_CONFIG.get("SAMPLE_SIZE")
    cn_test_code = STRATEGY_CONFIG.get("CN_TEST_CODE")

    if sample_size and isinstance(sample_size, int) and sample_size > 0:
        target_symbols = random.sample(all_codes, min(sample_size, len(all_codes)))
        print(f"🧪 [模式] 测试模式 {sample_size} 样本数")
    elif len(cn_test_code) > 0:
        target_symbols = cn_test_code
        print(f"🧪 [模式] 测试模式 {len(cn_test_code)} 样本数")
    else:
        target_symbols = all_codes
        print(f"🚀 [模式] 全量扫描")

    scanner = MarketScanner()

    await scanner.run_full_scan(target_symbols)

@timer
def main():
    log_dir = PATH_CONFIG.get("OUTPUT_LOG", "logs")

    with LogRedirector(log_folder=log_dir):
        print(f"{'▒' * 58}\n{'⚙️ Asian Quant | 策略计算引擎 ⚡':^58}\n{'▒' * 58}")
        try:
            asyncio.run(start_app())

        except KeyboardInterrupt:
            print("\n🛑 [停止] 用户手动中断了程序运行")
        except Exception as e:
            print(f"\n❌ [崩溃] 系统发生严重异常 {e}")

if __name__ == "__main__":
    main()