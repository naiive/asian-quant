#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Sequence, Any, Callable, List, Dict
from tqdm import tqdm
from conf.config import SYSTEM_CONFIG

async def run_dispatch(
    symbols: Sequence[str],
    worker_func: Callable[[str], Any],
    prepare_hook: Optional[Callable] = None,
    finalize_hook: Optional[Callable[[List[Any]], None]] = None,
    desc: str = "job name"
) -> List[Any]:
    """
      Args:
          symbols: 待处理的任务标识列表
          worker_func: 接收单个 symbol
          prepare_hook:【钩子】执行前的准备工作函数
          finalize_hook:【钩子】全部完成后执行的函数
          desc: 进度条左侧显示的描述文字
      Returns:
          List: 汇总后的所有命中结果列表
      """
    if not symbols:
        return []

    # 1.预处理阶段
    if prepare_hook:
        if asyncio.iscoroutinefunction(prepare_hook):
            await prepare_hook()
        else:
            prepare_hook()

    # 2.分批策略
    batch_size = SYSTEM_CONFIG.get("BATCH_SIZE", 500)

    batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]

    all_matched = []

    max_workers = SYSTEM_CONFIG.get("MAX_WORKERS", os.cpu_count())

    interval = SYSTEM_CONFIG.get("BATCH_INTERVAL_SEC", 1)

    loop = asyncio.get_running_loop()

    # 3.执行器管理
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for i, batch in enumerate(batches):
            print(f"\n🔢 [批次] {i + 1}/{len(batches)} 共计 {len(batch)} 支标的")

            strategy_counts: Dict[str, int] = {}

            tasks = [loop.run_in_executor(executor, worker_func, s) for s in batch]

            # 4.进度监控
            with tqdm(total=len(tasks), desc=f"🚨 {desc}", dynamic_ncols=True, leave=True) as pbar:

                for coro in asyncio.as_completed(tasks):
                    res = await coro
                    if res:
                        items = res if isinstance(res, list) else [res]
                        for item in items:
                            if isinstance(item, dict):
                                all_matched.append(item)
                                for s_name in item.keys():
                                    strategy_counts[s_name] = strategy_counts.get(s_name, 0) + 1

                        sorted_hits = sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True)

                        postfix_str = " | ".join([f"{name}:{count}" for name, count in sorted_hits])

                        total_hits = sum(strategy_counts.values())

                        pbar.set_postfix_str(f"{postfix_str} | total:{total_hits}")

                    pbar.update(1)

            # 5.流控机制
            if i < len(batches) - 1 and interval > 0:
                await asyncio.sleep(interval)

    # 6.收尾阶段
    if finalize_hook:
        finalize_hook(all_matched)

    return all_matched