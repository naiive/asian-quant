#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import pandas as pd
import numpy as np
from typing import Optional
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from core.client.mysql import MySQLClient

mpl.rcParams['font.sans-serif'] = ['Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False

def ensure_output_dir(table_name: str, x_axis_col: str, y_axis_col: str, x_step: int, y_step: int, start_date: str, end_date: str, min_market_cap: int, max_market_cap: int):
    """创建嵌套子目录"""
    current_script_dir = os.path.dirname(os.path.abspath(__file__))

    level1_dir = os.path.join(current_script_dir, table_name.split("_")[0])

    date_range_str = f"{start_date}_{end_date}"

    level2_dir = os.path.join(level1_dir, date_range_str)

    min_label = min_market_cap if min_market_cap is not None else "0"

    max_label = max_market_cap if max_market_cap is not None else "inf"

    market_cap_range_str = f"{min_label}_{max_label}"

    level3_dir = os.path.join(level2_dir, market_cap_range_str)

    level4_name = f"x_{x_axis_col}_{x_step}_y_{y_axis_col}_{y_step}"

    final_dir = os.path.join(level3_dir, level4_name)

    if not os.path.exists(final_dir):
        os.makedirs(final_dir)
        print(f"📁 已建立归档路径: {final_dir}")

    return final_dir


def query_data_from_mysql(sql: str, table_name: str, x_col: str, y_col: str):
    """从数据库加载策略原始数据"""
    mc = MySQLClient()

    print(f"🔍 正在读取数据库: {table_name} | X: {x_col} ｜ Y: {y_col}")

    try:
        df = mc.query_to_df(sql)

        if df is None or df.empty:
            print("⚠️ 未发现有效数据。")
            return None, None

        fc_cols = [col for col in df.columns if col.lower().startswith('fc')]
        numeric_cols = fc_cols + [y_col, x_col]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df_valid = df.dropna(subset=fc_cols, how='all').copy()
        df_valid = df_valid.rename(columns={y_col: 'Y轴数据', x_col: 'X轴数据'})

        print(f"✅ 成功加载 {len(df_valid)} 行有效数据")
        return fc_cols, df_valid

    except Exception as e:
        print(f"❌ 数据库读取错误: {e}")
        return None, None


def analyze_strategy(sql: str, tabel_name: str, x_axis_col: str, y_axis_col: str, x_step: int, y_step: int, start_date: str, end_date: str, min_market_cap: Optional[int] = None, max_market_cap: Optional[int] = None):
    """金融分箱统计与机器学习归因"""
    output_filename = "factor_distribution.csv"

    output_dir = ensure_output_dir(tabel_name, x_axis_col, y_axis_col, x_step, y_step, start_date, end_date, min_market_cap, max_market_cap)

    save_path = os.path.join(output_dir, output_filename)

    if os.path.exists(save_path):
        print(f"♻️ 检测到历史分析数据，跳过计算直接读取: {save_path}")
        return save_path

    output_dir = ensure_output_dir(tabel_name, x_axis_col, y_axis_col, x_step, y_step, start_date, end_date, min_market_cap, max_market_cap)

    fc_cols, df_valid = query_data_from_mysql(sql, tabel_name, x_axis_col, y_axis_col)

    if df_valid is None:
        return None

    target_fc = fc_cols[-1]
    rf_data = df_valid[['Y轴数据', 'X轴数据', target_fc]].dropna()

    if len(rf_data) > 30:
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(rf_data[['Y轴数据', 'X轴数据']], rf_data[target_fc])
        importances = rf.feature_importances_
        print(f"\n联合影响力归因: {y_axis_col}({importances[0]:.2%}) vs {x_axis_col}({importances[1]:.2%})")

    def get_bins(series, step):
        return np.arange(np.floor(series.min() / step) * step, np.ceil(series.max() / step) * step + step, step)

    df_valid.loc[:, 'Y轴区间'] = pd.cut(df_valid['Y轴数据'], bins=get_bins(df_valid['Y轴数据'], y_step))
    df_valid.loc[:, 'X轴区间'] = pd.cut(df_valid['X轴数据'], bins=get_bins(df_valid['X轴数据'], x_step))

    all_series = []
    cnts = df_valid.groupby(['Y轴区间', 'X轴区间'], observed=False)[fc_cols[0]].size()
    cnts.name = ('全局', '样本数')
    all_series.append(cnts)

    for fc in fc_cols:
        g = df_valid.groupby(['Y轴区间', 'X轴区间'], observed=False)[fc]
        m, s, n = g.mean(), g.std(), g.count()

        win_rate = g.apply(lambda x: (x.dropna() > 0).sum() / len(x.dropna()) if len(x.dropna()) > 0 else 0) * 100

        def calc_pl_ratio(x):
            x = x.dropna()
            pos, neg = x[x > 0].mean(), abs(x[x <= 0].mean())
            return pos / neg if neg > 0 and not np.isnan(neg) else np.nan

        all_series.append(m.apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "").rename((fc, '均值%')))
        all_series.append(win_rate.apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "").rename((fc, '胜率%')))
        all_series.append(g.apply(calc_pl_ratio).apply(lambda x: f"{x:.2f}" if pd.notna(x) else "").rename((fc, '盈亏比')))
        all_series.append((m / s).apply(lambda x: f"{x:.2f}" if pd.notna(x) else "").rename((fc, '夏普比')))
        all_series.append((m / (s / np.sqrt(n))).apply(lambda x: f"{x:.2f}" if pd.notna(x) else "").rename((fc, 'T值')))
        all_series.append(g.apply(lambda x: stats.ttest_1samp(x.dropna(), 0)[1] if len(x.dropna()) > 5 else 1.0).apply(lambda x: f"{x:.4f}" if pd.notna(x) else "").rename((fc, 'P值')))

    final_report = pd.concat(all_series, axis=1)
    final_report.columns = pd.MultiIndex.from_tuples(final_report.columns)
    save_path = os.path.join(output_dir, output_filename)
    final_report.to_csv(save_path)
    print(f"🚀 CSV报告已存入: {save_path}")

    return save_path


def draw_heatmap(file_path: str, target_period: str, min_samples: int, x_label: str, y_label: str, min_market_cap: Optional[int] = None, max_market_cap: Optional[int] = None):
    """
    功能：以盈亏比为核心色彩，整合夏普、T值、P值进行多维度热力图展示
    :param file_path: 文件名
    :param target_period: fc
    :param min_samples: 过滤的样本数下限
    :param x_label: 绘图显示的 X 轴名称
    :param y_label: 绘图显示的 Y 轴名称
    :param min_market_cap: 绘图右上角文字说明最小市值
    :param max_market_cap: 绘图右上角文字说明最大市值
    """

    if not os.path.exists(file_path): return

    output_dir = os.path.dirname(file_path)

    if not os.path.exists(file_path):
        print(f"❌ 找不到文件: {file_path}")
        return

    # 1. 读取数据并处理 MultiIndex 结构
    all_data = pd.read_csv(filepath_or_buffer=str(file_path), header=None, low_memory=False)
    periods = all_data.iloc[0].ffill()
    metrics = all_data.iloc[1]

    # 2. 定位该周期下所有指标的列索引
    cols_map = {}
    target_metrics = ["盈亏比", "夏普比", "T值", "P值", "均值%", "胜率%"]

    for i in range(len(periods)):
        p_name = str(periods[i]).strip()
        m_name = str(metrics[i]).strip()
        if p_name == target_period:
            if m_name in target_metrics:
                cols_map[m_name] = i

    if "盈亏比" not in cols_map:
        print(f"❌ 在周期 {target_period} 中未找到完整指标，请检查CSV表头")
        return

    # 3. 提取数据 (0,1 列是 Y轴和X轴区间)
    needed_cols = [0, 1, 2, cols_map["盈亏比"], cols_map["夏普比"], cols_map["T值"], cols_map["P值"], cols_map["均值%"], cols_map["胜率%"]]
    data = all_data.iloc[3:][needed_cols].copy()
    data.columns = ['Y轴', 'X轴', '样本数', '盈亏比', '夏普', 'T值', 'P值', '均值', '胜率']

    # 4. 强制数值化
    for col in ['样本数', '盈亏比', '夏普', 'T值', 'P值', '均值', '胜率']:
        data[col] = pd.to_numeric(data[col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

    # 5. 透视表转换
    pivot_pl = data.pivot(index='Y轴', columns='X轴', values='盈亏比')
    pivot_cnt = data.pivot(index='Y轴', columns='X轴', values='样本数')
    pivot_sp = data.pivot(index='Y轴', columns='X轴', values='夏普')
    pivot_t = data.pivot(index='Y轴', columns='X轴', values='T值')
    pivot_p = data.pivot(index='Y轴', columns='X轴', values='P值')
    pivot_mean = data.pivot(index='Y轴', columns='X轴', values='均值')
    pivot_win = data.pivot(index='Y轴', columns='X轴', values='胜率')

    # 6. 样本量过滤
    mask_valid = pivot_cnt >= min_samples
    valid_rows = mask_valid.any(axis=1)
    valid_cols = mask_valid.any(axis=0)

    pivot_pl = pivot_pl.loc[valid_rows, valid_cols]
    pivot_cnt = pivot_cnt.loc[valid_rows, valid_cols]
    pivot_sp = pivot_sp.loc[valid_rows, valid_cols]
    pivot_t = pivot_t.loc[valid_rows, valid_cols]
    pivot_p = pivot_p.loc[valid_rows, valid_cols]
    pivot_mean = pivot_mean.loc[valid_rows, valid_cols]
    pivot_win = pivot_win.loc[valid_rows, valid_cols]

    # 7. 排序逻辑
    def get_sort_key(interval_str):
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(interval_str))
        return float(nums[0]) if nums else 0

    sorted_cols = sorted(pivot_pl.columns, key=get_sort_key)
    sorted_idx = sorted(pivot_pl.index, key=get_sort_key, reverse=True)

    pivot_pl = pivot_pl.reindex(index=sorted_idx, columns=sorted_cols)
    pivot_cnt = pivot_cnt.reindex(index=sorted_idx, columns=sorted_cols)
    pivot_sp = pivot_sp.reindex(index=sorted_idx, columns=sorted_cols)
    pivot_t = pivot_t.reindex(index=sorted_idx, columns=sorted_cols)
    pivot_p = pivot_p.reindex(index=sorted_idx, columns=sorted_cols)
    pivot_mean = pivot_mean.reindex(index=sorted_idx, columns=sorted_cols)
    pivot_win = pivot_win.reindex(index=sorted_idx, columns=sorted_cols)

    # 8. 构建多行文字标注
    def make_annot(pl, cnt, sp, tv, pv, mn, wr):
        if cnt < min_samples: return ""
        sig = "**" if pv <= 0.05 else ""
        # 第一行：盈亏比(样本数) 夏普 | 均值% | P值 | T值 | 胜率%
        return f"{pl:.2f} ({int(cnt)})\nS:{sp:.2f} | A:{mn:.2f}%\n{sig}P:{pv:.3f} | T:{tv:.1f} | W:{wr:.1f}%"

    v_func = np.vectorize(make_annot)
    annot_text = v_func(pivot_pl, pivot_cnt, pivot_sp, pivot_t, pivot_p, pivot_mean, pivot_win)

    # 9. 绘图
    plt.figure(figsize=(25, 13))
    sns.heatmap(
        pivot_pl.where(pivot_cnt >= min_samples),
        annot=annot_text,
        fmt="",
        cmap="RdYlGn",
        center=1.0,
        linewidths=0.1,
        linecolor='#f0f0f0',
        cbar_kws={'label': '盈亏比 (P/L Ratio)'},
        annot_kws={"size": 6, "weight": "normal"}
    )

    if min_market_cap is None and max_market_cap is None:
        text_right = "注：样本总市值全覆盖 (不限)"
    elif min_market_cap is None:
        text_right = f"注：样本总市值 <{max_market_cap} 亿"
    elif max_market_cap is None:
        text_right = f"注：样本总市值 >{min_market_cap} 亿"
    else:
        text_right = f"注：样本总市值 {min_market_cap}~{max_market_cap} 亿"
    plt.text(1.0, 1.02, text_right, transform=plt.gca().transAxes, ha='right', fontsize=9)
    plt.title(f'【{target_period.upper()}】{y_label} vs {x_label} 多维度共振分析 | 过滤样本 >{min_samples}\n【基础: 盈亏比 >1.5 | 夏普比 >1.0 | T值 >2.0 | P值 <0.05】', fontsize=12)
    plt.xlabel(f'{x_label} 区间', fontsize=9)
    plt.ylabel(f'{y_label} 区间', fontsize=9)
    plt.tight_layout()

    out_name = f"{target_period.lower()}.png"
    plt.savefig(os.path.join(output_dir, out_name), dpi=300)

    plt.close()

    print(f"✅ 热力图已保存: {out_name}")


if __name__ == "__main__":

    TABLE_NAME = 'cro_strategy_table'
    START_DATE, END_DATE = '2024-01-01', '2026-01-01'
    X_COL_NAME, X_DISPLAY, X_STEP = 'wtc_value', '数值', 1
    Y_COL_NAME, Y_DISPLAY, Y_STEP = 'wtc_green', '绿色', 5
    # 输入 5          -> fc5
    # 输入 "1~5"      -> fc1, fc2, fc3, fc4, fc5
    # 输入 [1, 4, 5]  -> fc1, fc4, fc5
    DAYS = [20, 30]
    MIN_SAMPLES = 30
    MIN_MARKET_CAP, MAX_MARKET_CAP = None, None
    conds = [f"{Y_COL_NAME} IS NOT NULL", f"{X_COL_NAME} IS NOT NULL", f"trade_date >= '{START_DATE}'", f"trade_date <= '{END_DATE}'"]
    if MIN_MARKET_CAP is not None: conds.append(f"market_cap >= {MIN_MARKET_CAP}")
    if MAX_MARKET_CAP is not None: conds.append(f"market_cap <= {MAX_MARKET_CAP}")
    SQL = f"SELECT * FROM {TABLE_NAME} WHERE " + " AND ".join(conds)

    # 1. 运行分析
    csv_path = analyze_strategy(
        sql=SQL,
        tabel_name=TABLE_NAME,
        x_axis_col=X_COL_NAME, x_step=X_STEP,
        y_axis_col=Y_COL_NAME, y_step=Y_STEP,
        start_date=START_DATE, end_date=END_DATE,
        min_market_cap=MIN_MARKET_CAP, max_market_cap=MAX_MARKET_CAP
    )

    # 2. 生成图表
    if csv_path:
        if isinstance(DAYS, int):
            day_list = [DAYS]
        elif isinstance(DAYS, str) and "~" in DAYS:
            try:
                start, end = map(int, DAYS.split("~"))
                day_list = list(range(start, end + 1))
            except ValueError:
                day_list = []
        elif isinstance(DAYS, (list, tuple, range)):
            day_list = list(DAYS)
        else:
            day_list = []
        final_days = sorted(list(set(d for d in day_list if 1 <= d <= 30)))

        for d in final_days:
            draw_heatmap(
                file_path=csv_path,
                target_period=f'fc{d}',
                min_samples=MIN_SAMPLES,
                x_label=X_DISPLAY, y_label=Y_DISPLAY,
                min_market_cap=MIN_MARKET_CAP, max_market_cap=MAX_MARKET_CAP
            )