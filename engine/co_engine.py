#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import concurrent.futures
from datetime import datetime
from pathlib import Path
import pandas as pd

from conf.config import STRATEGY_CONFIG
from core.client.api import APIClient
from core.util.decorator import retry
from core.util.func import get_unified_interval
from strategies.moo_strategy import run_strategy

_api = APIClient()

EXCHANGE_META = {
    "O": "OKX",
    "B": "Binance",
}

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG = {
    "exchange": STRATEGY_CONFIG.get("CO_EXCHANGE", "B"),
    "interval": STRATEGY_CONFIG.get("CO_INTERVAL", "15m"),
    "limit": STRATEGY_CONFIG.get("CO_KLINE_LIMIT", 300),
    "max_workers": STRATEGY_CONFIG.get("CO_MAX_WORKERS", 8),
    "manual_list": STRATEGY_CONFIG.get("CO_MANUAL_LIST", []),
    "end_time": STRATEGY_CONFIG.get("CO_END_DAY", None),
    "top_n": STRATEGY_CONFIG.get("CO_TOP_N", 300),
    "rank_by": STRATEGY_CONFIG.get("CO_RANK_BY", "volume"),
    "save_csv": True,
    "output_dir": BASE_DIR / "data/symbols",
}

def build_crypto_pool(cfg: dict) -> list[dict]:
    raw_list = cfg.get("manual_list", [])
    exchange = cfg["exchange"]

    if raw_list:
        pool = [
            {"code": f"{base.upper()}-USDT", "name": base.upper()}
            for base in raw_list
            if str(base).strip()
        ]
        print(f"✏️ 手动精选列表加载成功  [{exchange}]  共 {len(pool)} 只\n")
    else:
        print(
            f"🌐 启动全市场快照实时筛选 (RankBy={cfg['rank_by']}, TopN={cfg['top_n']})..."
        )
        pool = _api.fetch_crypto_market_snapshot(
            exchange=exchange,
            top_n=cfg["top_n"],
            rank_by=cfg["rank_by"]
        )
        print(
            f"📋 动态大盘过滤排序完成  [{EXCHANGE_META[exchange]}]  实际入池扫描: {len(pool)} 只标的\n"
        )

    return pool

@retry(max_retries=2, delay=1)
def run_single(
    item: dict, exchange: str, interval: str, limit: int, end_time: str | None
) -> list[dict]:
    code, name = item["code"], item["name"]
    hits: list[dict] = []

    try:
        df = _api.fetch_crypto_klines(
            exchange=exchange,
            symbol=code,
            interval=interval,
            limit=limit,
            end_time=end_time,
        )

        if df.empty or len(df) < 20:
            return hits

        for result in run_strategy(df, code):
            result["名称"] = name
            result["周期"] = interval.upper()
            result["交易所"] = EXCHANGE_META[exchange]
            hits.append(result)

    except Exception as e:
        print(f"  ⚠️  {code}: {e}")

    return hits

def scan_signals(pool: list[dict], cfg: dict) -> pd.DataFrame:
    exchange = cfg["exchange"]
    interval = cfg["interval"]
    limit = cfg["limit"]
    end_time = cfg["end_time"]
    total = len(pool)
    ex_name = EXCHANGE_META[exchange]

    print(
        f"🚀 开始扫描 {total} 只标的"
        f"[{ex_name}]  interval={interval}  limit={limit}  end_time={end_time or 'Latest'}\n"
    )

    results: list[dict] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=cfg["max_workers"]
    ) as executor:
        future_to_item = {
            executor.submit(
                run_single, item, exchange, interval, limit, end_time
            ): item
            for item in pool
        }

        for i, future in enumerate(
            concurrent.futures.as_completed(future_to_item), 1
        ):
            item = future_to_item[future]
            try:
                hits = future.result()
                if hits:
                    results.extend(hits)
                    print(
                        f"  [{i:>3}/{total}] ✅  {item['code']}  {item['name']}  ({len(hits)} 个信号)"
                    )
                else:
                    print(f"  [{i:>3}/{total}]     {item['code']}  {item['name']}")
            except Exception as e:
                print(f"  [{i:>3}/{total}] ❌  {item['code']}  {item['name']} : {e}")

    if not results:
        print("\n📭 本次扫描无信号")
        return pd.DataFrame()

    return pd.DataFrame(results)

def main():
    pool = build_crypto_pool(CONFIG)
    if not pool:
        print("❌ 未筛选到可用的交易标的，扫描提前结束。")
        return

    signals = scan_signals(pool, CONFIG)

    if not signals.empty:
        print(f"\n🎯 共发现 {len(signals)} 个量化信号:\n")
        print(signals.to_string(index=False))

        if CONFIG["save_csv"]:
            out_dir = Path(CONFIG["output_dir"])
            date_dir = out_dir / datetime.today().strftime("%Y%m%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            end_str = datetime.strptime(CONFIG["end_time"].lower(), '%Y-%m-%d').strftime('%m%d')
            interval_str = get_unified_interval(str(STRATEGY_CONFIG.get("CO_INTERVAL")).lower().strip())
            filename = date_dir / f"{interval_str}_cyt_{end_str}_{datetime.today().strftime('%H:%M:%S')}.csv"
            signals.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n💾 信号文件已成功归档: {filename}")

if __name__ == "__main__":
    main()