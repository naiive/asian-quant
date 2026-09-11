#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import pandas as pd

from conf.config import SYSTEM_CONFIG
from core.client.api import APIClient

def enrich_results(df_res: pd.DataFrame, handler=None, df_live: pd.DataFrame | None = None) -> pd.DataFrame:
    """多股票信息一次查询"""
    if df_res is None or df_res.empty:
        return df_res

    try:
        if df_live is None:
            if handler is not None and getattr(handler, 'api_client', None) is not None:
                df_live = handler.api_client.fetch_realtime_snapshot()
            elif APIClient is not None:
                df_live = APIClient().fetch_realtime_snapshot()
            else:
                df_live = pd.DataFrame()

        if df_live is None or df_live.empty:
            return df_res

        info_cols = ['code', 'name', 'turnover', 'pe', 'mcap', 'ffmc', 'ytd']
        df_info = df_live[[c for c in info_cols if c in df_live.columns]]

        df_enriched = pd.merge(df_res, df_info, left_on='代码', right_on='code', how='left')

        if 'code' in df_enriched.columns:
            df_enriched.drop(columns=['code'], inplace=True)

        head_cols = ['turnover', 'pe', 'mcap', 'ffmc', 'ytd']
        head_cols = [c for c in head_cols if c in df_enriched.columns]
        others = [c for c in df_enriched.columns if c not in head_cols]

        if 'name' in others:
            others = [c for c in others if c != 'name']
            others.insert(2, 'name')

        sorted_df = df_enriched[others + head_cols]

        export_map = {
            'name': '名称',
            'turnover': '换手率(%)',
            'pe': '市盈率(动)',
            'mcap': '总市值(亿)',
            'ffmc': '流通市值(亿)',
            'ytd': '年涨幅(%)'
        }

        return sorted_df.rename(columns=export_map)

    except Exception as e:
        print(f"⚠️ [警告] enrich_results 过程出错 {e}")
        return df_res

def enrich_results_v2(df_res: pd.DataFrame, handler=None) -> pd.DataFrame:
    """单股票信息一次查询"""
    if df_res is None or df_res.empty:
        return df_res

    try:
        target_codes = df_res['代码'].unique().tolist()
        details_list = []

        for code in target_codes:
            try:
                method = getattr(handler, 'fetch_individual_info', getattr(getattr(handler, 'mysql_client', None), 'fetch_individual_info', None))
                if method and callable(method):
                    df_item = method(code)
                    if df_item is not None:
                        details_list.append(df_item)
            except Exception as e:
                print(f"⚠️ [警告] 信息补充 {code} 失败 {e}")
                continue

        if not details_list:
            return df_res

        df_details_all = pd.concat(details_list, ignore_index=True)
        df_info_subset = df_details_all.copy()

        df_res['代码'] = df_res['代码'].astype(str)
        df_info_subset['code'] = df_info_subset['code'].astype(str)

        df_enriched = pd.merge(df_res, df_info_subset, left_on='代码', right_on='code', how='left')

        if 'code' in df_enriched.columns:
            df_enriched.drop(columns=['code'], inplace=True)

        cols = list(df_enriched.columns)
        if 'name' in cols:
            cols.remove('name')
            idx = cols.index('代码') + 1 if '代码' in cols else 0
            cols.insert(idx, 'name')
        df_enriched = df_enriched[cols]

        export_map = {
            'name': '名称',
            'industry': '行业',
            'mcap': '总市值(亿)',
            'ffmc': '流通市值(亿)'
        }

        df_enriched = df_enriched[df_enriched['ffmc'] >= SYSTEM_CONFIG["TRADABLE_MARKET_VALUE"]]

        return df_enriched.rename(columns=export_map)

    except Exception as e:
        print(f"⚠️ enrich_results_v2 错误: {e}")
        return df_res

def enrich_future_changes(df_res: pd.DataFrame, handler=None, days_list=None) -> pd.DataFrame:
    """当前日期未来累积涨幅"""
    if df_res is None or df_res.empty:
        return df_res

    df_res['代码'] = df_res['代码'].astype(str).str.zfill(6)
    target_codes = df_res['代码'].unique().tolist()

    method = getattr(handler.mysql_client, 'fetch_future_changes', None)
    features_list = []

    for code in target_codes:
        base_date = df_res[df_res['代码'] == code]['日期'].iloc[0]
        try:
            df_feat = method(code, start_date=base_date, lookback_list=days_list)
            if df_feat is not None and not df_feat.empty:
                df_feat['code'] = df_feat['code'].astype(str).str.zfill(6)
                features_list.append(df_feat.astype(object))
        except Exception as e:
            print(f"⚠️ 处理 {code} 时发生错误: {e}")
            continue

    if not features_list:
        return df_res

    df_features_all = pd.concat(features_list, ignore_index=True, sort=False)

    df_enriched = pd.merge(df_res, df_features_all, left_on='代码', right_on='code', how='left')

    drop_cols = ['code', 'base_date']
    df_enriched.drop(columns=[c for c in drop_cols if c in df_enriched.columns], inplace=True, errors='ignore')

    df_enriched = df_enriched.astype(object).where(pd.notnull(df_enriched), None)

    return df_enriched

def upsert_results_to_mysql(df_res: pd.DataFrame, strategy_name: str, handler=None):
    """负责字段映射与清洗"""
    if df_res is None or df_res.empty:
        return df_res

    base_mapping = {
        '日期': 'trade_date',
        '代码': 'symbol',
        '名称': 'name',
        '现价': 'last_price',
        '涨幅(%)': 'pct_chg',
        '成交量': 'volume',
        '换手(%)': 'turnover_rate',
        '止损': 'stop_loss',
        'FVG': 'fvg',
        'VFI': 'vfi',
        "AVWAP": 'anchored_vwap',
        "BIAS": 'anchored_vwap_bias',
        '行业': 'industry',
        'EMA': 'ema',
        'RSI': 'rsi',
        'STO': 'stochastic_rsi',
        '总市值(亿)': 'market_cap',
        '流通市值(亿)': 'float_cap',
        "龙虎榜": 'is_lhb',
        "上榜解读": 'interpretation',
        "上榜原因": 'list_reason',
        "一级行业": 'level1_name',
        "二级行业": 'level2_name',
        "三级行业": 'level3_name',
        '参数': 'strategy_params',
        '条件': 'condition',
        '参组': 'label_params'
    }

    for i in range(1, 31):
        base_mapping[f'FC{i}'] = f'fc{i}'

    strategy_config = {
        'sqz': (
            'sqz_strategy_table',
            {
                '释放': 'release',
                'PSQ': 'price_sequence',
                'TSQ': 'trend_sequence',
                'RSQ': 'pct_sequence',
                'SCO': 'pct_score',
                'STC': 'stc_trend',
                'BSA': 'bars_since_anchor',
                'RPT': 'range_pct',
                '挤压': 'sqz_val',
                '判断': 'judgment',
                '分数': 'score_info'
            }
        ),
        'low': (
            'low_strategy_table',
            {
                'RSI14': 'rsi14',
                'RSI26': 'rsi26',
                'KDJ_J': 'kdj_j',
                'PRE_KDJ_J': 'pre_kdj_j',
                'CCI': 'cci',
                'PRE_CCI': 'pre_cci',
                'OBV背离': 'obv_divergence',
                '量比': 'vol_ratio',
                '缩量': 'vol_shrink',
                '绿线': 'wtc_green',
                'MA200': 'ma200',
                'MA200偏离(%)': 'ma200_dev'
            }
        )
    }

    conf = strategy_config.get(strategy_name.lower())
    if not conf:
        print(f"❌ [错误] 未定义 {strategy_name}策略 upsert表结构")
        return df_res

    table_name, extra_mapping = conf
    full_mapping = {**base_mapping, **extra_mapping}

    df_to_mysql = df_res.copy()
    df_to_mysql = df_to_mysql.rename(columns=full_mapping)
    valid_db_cols = [c for c in df_to_mysql.columns if c in full_mapping.values()]
    df_to_mysql = df_to_mysql[valid_db_cols]

    if handler and hasattr(handler, 'mysql_client'):
        handler.mysql_client.upsert_table(df_to_mysql, table_name)
    else:
        print(f"❌ [失败] 未找到mysql实例")

    return df_res