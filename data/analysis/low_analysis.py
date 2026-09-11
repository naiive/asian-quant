#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from core.client.mysql import MySQLClient

"""
行业底部聚合
"""

mc = MySQLClient()

# ══ 参数配置 ══════════════════════════════════════════════
# 优先级：START_DATE+END_DATE > TRADE_DATE > 自动最新
LEVEL              = "3"
TRADE_DATE         = '2026-03-09'   # 单日：'2026-02-27'，None = 自动取最新一天
START_DATE         = '2026-03-31'   # 时间段：开始日期 '2026-01-01'
END_DATE           = '2026-04-08'   # 时间段：结束日期 '2026-02-27'

ROLL_DAYS          = 5              # 滚动窗口（仅单日模式使用）
MIN_STOCK_COUNT    = 5              # 行业最少个股数，低于此排除
OVERSOLD_RATIO_THR = 0.40           # 超卖比例触发阈值

KDJ_J_TURN_THR     = 30             # KDJ-J 触底上翻判断阈值
CCI_TURN_THR       = -100           # CCI 从超卖区上翻判断阈值
RSI14_OVERSOLE     = 30             # 普通超卖阈值
RSI14_EXTREME      = 20             # 极度超卖阈值
MA200_DEV_FLOOR    = -0.40          # MA200 偏离下限，低于此视为基本面风险

def load_signals(trade_date=None, start_date=None, end_date=None):
    if start_date and end_date:
        where = f"t.trade_date >= '{start_date}' AND t.trade_date <= '{end_date}'"
        print(f"[加载] 时间段: {start_date} ~ {end_date}")
    else:
        if trade_date is None:
            trade_date = str(mc.query_to_df(
                "SELECT MAX(trade_date) as d FROM low_strategy_table"
            )['d'].iloc[0])
        where = f"t.trade_date = '{trade_date}'"
        print(f"[加载] 单日: {trade_date}")

    sql = f"""
        SELECT
            t.trade_date,
            t.symbol,
            s.level{LEVEL}_name AS industry,
            t.rsi14, t.rsi26,
            t.kdj_j, t.pre_kdj_j,
            t.cci, t.pre_cci,
            t.vol_ratio, t.vol_shrink,
            t.obv_divergence, t.wtc_green, t.ma200_dev
        FROM low_strategy_table t
        LEFT JOIN sw_stock_industry s
            ON LEFT(t.symbol, 6) = s.stock_code COLLATE utf8mb4_unicode_ci
        WHERE {where}
          AND s.level{LEVEL}_name IS NOT NULL
        ORDER BY t.trade_date ASC
    """
    df = mc.query_to_df(sql)
    dates = sorted(df['trade_date'].astype(str).unique().tolist())
    print(f"[加载] {len(df)} 条记录，{len(dates)} 个交易日，{df['industry'].nunique()} 个行业")
    return df, dates


def load_rolling_signals(trade_date, days=5):
    """过去 N 个交易日的个股记录，用于滚动超卖统计（单日模式）"""
    sql = f"""
        SELECT t.trade_date, t.symbol, s.level{LEVEL}_name AS industry
        FROM low_strategy_table t
        LEFT JOIN sw_stock_industry s
            ON LEFT(t.symbol, 6) = s.stock_code COLLATE utf8mb4_unicode_ci
        WHERE t.trade_date <= '{trade_date}'
          AND s.level{LEVEL}_name IS NOT NULL
        ORDER BY t.trade_date DESC
    """
    df = mc.query_to_df(sql)
    recent = pd.to_datetime(df['trade_date']).drop_duplicates().nlargest(days).tolist()
    return df_all[df_all['trade_date'].isin(recent)]

def load_total_counts():
    """从 sw_stock_industry 统计各 level_name 行业的申万成分股总数（分母）"""
    sql = f"""
        SELECT level{LEVEL}_name AS industry, COUNT(*) AS total_count
        FROM sw_stock_industry
        WHERE level{LEVEL}_name IS NOT NULL
        GROUP BY level{LEVEL}_name
    """
    return mc.query_to_df(sql)


def aggregate_industry(df, roll, total, is_range=False):
    """个股明细 → 行业聚合"""
    df = df.copy()

    df['kdj_turn']     = (df['kdj_j'] < KDJ_J_TURN_THR) & (df['kdj_j'] > df['pre_kdj_j'])
    df['cci_turn']     = (df['pre_cci'] < CCI_TURN_THR)  & (df['cci']   > df['pre_cci'])
    df['rsi_oversole'] = df['rsi14'] < RSI14_OVERSOLE
    df['rsi_extreme']  = df['rsi14'] < RSI14_EXTREME
    df['ma200_risk']   = df['ma200_dev'].notna() & (df['ma200_dev'] < MA200_DEV_FLOOR)

    agg = df.groupby('industry').agg(
        avg_rsi14     = ('rsi14',     'mean'),
        avg_kdj_j     = ('kdj_j',     'mean'),
        avg_cci       = ('cci',       'mean'),
        avg_vol_ratio = ('vol_ratio', 'mean'),
        avg_wtc_green = ('wtc_green', 'mean'),
    ).reset_index()

    per_stock = df.groupby(['industry', 'symbol']).agg(
        kdj_turn_hit   = ('kdj_turn',       'max'),
        cci_turn_hit   = ('cci_turn',        'max'),
        obv_div_hit    = ('obv_divergence',  lambda x: (x == '是').any()),
        vol_shrink_hit = ('vol_shrink',      lambda x: (x == '是').any()),
        oversole_hit   = ('rsi_oversole',    'max'),
        extreme_hit    = ('rsi_extreme',     'max'),
        ma200_risk_hit = ('ma200_risk',      'max'),
    ).reset_index()

    counts = per_stock.groupby('industry').agg(
        signal_count     = ('symbol',         'count'),
        kdj_turn_count   = ('kdj_turn_hit',   'sum'),
        cci_turn_count   = ('cci_turn_hit',   'sum'),
        obv_div_count    = ('obv_div_hit',    'sum'),
        vol_shrink_count = ('vol_shrink_hit', 'sum'),
        oversole_count   = ('oversole_hit',   'sum'),
        extreme_count    = ('extreme_hit',    'sum'),
        ma200_risk_count = ('ma200_risk_hit', 'sum'),
    ).reset_index()

    agg = agg.merge(counts, on='industry')

    agg = agg.merge(df_total, on='industry', how='left')
    agg['total_count'] = agg['total_count'].fillna(agg['signal_count'])
    agg = agg[agg['total_count'] >= MIN_STOCK_COUNT]
    agg['kdj_turn_ratio']   = agg['kdj_turn_count']    / agg['signal_count']
    agg['cci_turn_ratio']   = agg['cci_turn_count']    / agg['signal_count']
    agg['obv_div_ratio']    = agg['obv_div_count']     / agg['signal_count']
    agg['vol_shrink_ratio'] = agg['vol_shrink_count']  / agg['signal_count']
    agg['oversold_ratio']    = agg['oversole_count']     / agg['signal_count']
    agg['extreme_ratio']    = agg['extreme_count']     / agg['signal_count']

    if not is_range and roll is not None:
        roll_counts = (roll.groupby('industry')['symbol'].nunique().reset_index().rename(columns={'symbol': 'roll_count'}))
        agg = agg.merge(roll_counts, on='industry', how='left')
        agg = agg.merge(total.rename(columns={'total_count': 'ind_total'}), on='industry', how='left')
        agg['roll_5d_ratio'] = (agg['roll_count'] / agg['ind_total']).fillna(agg['oversold_ratio'])
    else:
        agg['roll_5d_ratio'] = None

    agg['bottom_grade'] = agg.apply(_grade, axis=1)
    grade_order = {'S': 0, 'A': 1, 'B': 2, 'C': 3}
    agg['_ord'] = agg['bottom_grade'].map(grade_order)
    agg = agg.sort_values(['_ord', 'oversold_ratio'], ascending=[True, False])
    return agg.drop(columns='_ord').reset_index(drop=True)


def _grade(row):
    if row['oversold_ratio'] < OVERSOLD_RATIO_THR:
        return 'C'
    has_reversal   = row['kdj_turn_ratio'] >= 0.3 or row['cci_turn_ratio'] >= 0.3
    has_exhaustion = row['obv_div_ratio']  >= 0.3 or row['vol_shrink_ratio'] >= 0.5
    has_extreme    = row['extreme_ratio']  >= 0.3
    if has_reversal and has_exhaustion:
        return 'S'
    if has_reversal or (has_exhaustion and has_extreme):
        return 'A'
    return 'B'


def save_html_report(results, labels, output_path=None):
    is_range = results['roll_5d_ratio'].isna().all()

    if output_path is None:
        safe = labels.replace(' ', '').replace('~', '_to_').replace('/', '-')[:40]
        output_path = f"industry_bottom_level{LEVEL}_{safe}.html"

    grade_meta = {
        'S': {'label': 'S级', 'desc': '三层共振 · 重点关注', 'color': '#ef4444', 'bg': '#1a0a0a'},
        'A': {'label': 'A级', 'desc': '信号较强 · 可以关注', 'color': '#f59e0b', 'bg': '#1a1200'},
        'B': {'label': 'B级', 'desc': '超卖达标 · 等待信号', 'color': '#3b82f6', 'bg': '#0a1628'},
        'C': {'label': 'C级', 'desc': '超卖不足 · 仅供参考', 'color': '#475569', 'bg': '#111827'},
    }

    def pct(v):
        try:
            return f"{float(v):.1%}"
        except IOError:
            return '—'

    def val(v, d=1):
        try:
            return f"{float(v):.{d}f}"
        except IOError:
            return '—'

    def tag_cls(v, thr):
        try: return 'tag-on' if float(v or 0) >= thr else 'tag-off'
        except IOError:
            return 'tag-off'

    def second_metric(rows):
        if is_range:
            return f'<div class="metric"><div class="metric-val">{pct(rows["oversold_ratio"])}</div><div class="metric-lbl">超卖宽度</div></div>'
        else:
            return f'<div class="metric"><div class="metric-val">{pct(rows["roll_5d_ratio"])}</div><div class="metric-lbl">滚动5日</div></div>'

    cards_html = ''
    for grade in ['S', 'A', 'B', 'C']:
        subset = result[result['bottom_grade'] == grade]
        if subset.empty:
            continue
        meta = grade_meta[grade]

        cards_html += f'''
        <div class="grade-section">
          <div class="grade-header" style="border-left:4px solid {meta["color"]}">
            <span class="grade-badge" style="background:{meta["color"]}">{meta["label"]}</span>
            <span class="grade-desc">{meta["desc"]}</span>
            <span class="grade-count">{len(subset)} 个行业</span>
          </div>
          <div class="cards-grid">'''

        for _, row in subset.iterrows():
            risk_html = ''
            if row.get('ma200_risk_count', 0) > 0:
                rp = row['ma200_risk_count'] / row['signal_count']
                risk_html = f'<div class="risk-tag">⚠ {pct(rp)} 个股距年线偏离 &gt;40%</div>'

            cards_html += f'''
            <div class="card" style="border-top:3px solid {meta["color"]};background:{meta["bg"]}">
              <div class="card-title">{row["industry"]}</div>
              <div class="card-sub">触发 {int(row["signal_count"])} / 共 {int(row["total_count"])} 只</div>
              <div class="metrics-row">
                <div class="metric">
                  <div class="metric-val" style="color:{meta["color"]}">{pct(row["oversold_ratio"])}</div>
                  <div class="metric-lbl">超卖比例</div>
                </div>
                {second_metric(row)}
                <div class="metric">
                  <div class="metric-val">{val(row["avg_rsi14"])}</div>
                  <div class="metric-lbl">RSI14均值</div>
                </div>
                <div class="metric">
                  <div class="metric-val">{pct(row["extreme_ratio"])}</div>
                  <div class="metric-lbl">极度超卖</div>
                </div>
              </div>
              <div class="divider"></div>
              <div class="tags-row">
                <div class="tag {tag_cls(row["kdj_turn_ratio"], 0.3)}">KDJ上翻 {pct(row["kdj_turn_ratio"])}</div>
                <div class="tag {tag_cls(row["cci_turn_ratio"], 0.3)}">CCI上翻 {pct(row["cci_turn_ratio"])}</div>
                <div class="tag {tag_cls(row["obv_div_ratio"],  0.3)}">OBV背离 {pct(row["obv_div_ratio"])}</div>
                <div class="tag {tag_cls(row["vol_shrink_ratio"],0.5)}">缩量 {pct(row["vol_shrink_ratio"])}</div>
              </div>
              <div class="extra-row">CRO绿线 {val(row["avg_wtc_green"])} &nbsp;|&nbsp; 量比均值 {val(row["avg_vol_ratio"],2)}</div>
              {risk_html}
            </div>'''

        cards_html += '</div></div>'

    s_cnt = len(result[result["bottom_grade"] == "S"])
    a_cnt = len(result[result["bottom_grade"] == "A"])
    b_cnt = len(result[result["bottom_grade"] == "B"])

    html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Level{LEVEL}行业底部扫描 · {labels}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+SC:wght@400;500;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans SC',sans-serif;background:#0c0e14;color:#e2e8f0;min-height:100vh;padding:32px 24px 64px}}
.header{{max-width:1200px;margin:0 auto 36px;border-bottom:1px solid #1e293b;padding-bottom:20px}}
.header-top{{display:flex;align-items:baseline;gap:16px;margin-bottom:8px}}
h1{{font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:600;color:#f8fafc;letter-spacing:-.5px}}
.header-date{{font-family:'IBM Plex Mono',monospace;font-size:12px;color:#64748b}}
.header-summary{{font-size:12px;color:#64748b}}
.header-summary span{{color:#94a3b8;margin-right:16px}}
.main{{max-width:1200px;margin:0 auto}}
.grade-section{{margin-bottom:36px}}
.grade-header{{display:flex;align-items:center;gap:12px;padding:10px 16px;background:#111827;border-radius:6px;margin-bottom:14px}}
.grade-badge{{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;color:#fff;padding:2px 8px;border-radius:3px;letter-spacing:.5px}}
.grade-desc{{font-size:13px;color:#94a3b8;flex:1}}
.grade-count{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#475569}}
.cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.card{{border-radius:8px;padding:16px;border:1px solid #1e293b;transition:transform .15s,box-shadow .15s}}
.card:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.5)}}
.card-title{{font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:3px}}
.card-sub{{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#475569;margin-bottom:14px}}
.metrics-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:12px}}
.metric{{text-align:center}}
.metric-val{{font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:600;line-height:1.2}}
.metric-lbl{{font-size:9px;color:#475569;margin-top:2px}}
.divider{{height:1px;background:#1e293b;margin:10px 0}}
.tags-row{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px}}
.tag{{font-family:'IBM Plex Mono',monospace;font-size:9px;padding:2px 6px;border-radius:3px;white-space:nowrap}}
.tag-on{{background:#14532d;color:#86efac;border:1px solid #166534}}
.tag-off{{background:#1e293b;color:#475569;border:1px solid #334155}}
.extra-row{{font-size:10px;color:#475569;font-family:'IBM Plex Mono',monospace}}
.risk-tag{{margin-top:7px;font-size:10px;color:#fbbf24;background:#1c1400;border:1px solid #78350f;border-radius:3px;padding:3px 7px}}
</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <h1>Level{LEVEL}行业底部扫描</h1>
    <span class="header-date">{labels}</span>
  </div>
  <div class="header-summary">
    <span>扫描行业 {len(results)} 个</span>
    <span>S级 {s_cnt} 个</span>
    <span>A级 {a_cnt} 个</span>
    <span>B级 {b_cnt} 个</span>
    <span>普通超卖 {RSI14_OVERSOLE}</span>
    <span>极端卖 {RSI14_EXTREME}</span>
  </div>
</div>
<div class="main">{cards_html}</div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[报告] 已生成 → {output_path}")


if __name__ == "__main__":
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)

    df_total = load_total_counts()

    if START_DATE and END_DATE:
        df_all, trade_dates = load_signals(start_date=START_DATE, end_date=END_DATE)
        label  = f"{START_DATE} ~ {END_DATE}（{len(trade_dates)} 个交易日）"
        result = aggregate_industry(df_all, roll=None, total=df_total, is_range=True)
        print(f"[聚合] {label}  →  {len(result)} 个行业")
        save_html_report(result, label)

    else:
        df_all, trade_dates = load_signals(trade_date=TRADE_DATE)
        td      = trade_dates[-1]
        df_roll = load_rolling_signals(td, days=ROLL_DAYS)
        result  = aggregate_industry(df_all, roll=df_roll, total=df_total, is_range=False)
        print(f"[聚合] {td}  →  {len(result)} 个行业")
        save_html_report(result, td)