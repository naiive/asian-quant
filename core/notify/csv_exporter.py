#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from typing import Optional
import pandas as pd
from conf.config import SYSTEM_CONFIG, PATH_CONFIG, STRATEGY_CONFIG
from core.util.func import get_unified_interval

def csv_exporter(df: Optional[pd.DataFrame], strategy_name: str = None) -> Optional[str]:

    interval_str = get_unified_interval(str(STRATEGY_CONFIG.get("CN_INTERVAL")).lower().strip())

    if SYSTEM_CONFIG.get("ENABLE_EXPORT") and df is not None:

        date_str = time.strftime('%Y%m%d')

        save_dir = os.path.join(PATH_CONFIG["OUTPUT_FOLDER_BASE"], date_str)

        os.makedirs(save_dir, exist_ok=True)

        trade_date = df.loc[0, '日期'].replace('-', '')[-4:]

        file_path = os.path.join(save_dir, f"{interval_str}_{strategy_name}_{trade_date}_{time.strftime('%H:%M:%S')}.csv")

        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        print(f"🎉 [{strategy_name}] 导出成功 {file_path}")