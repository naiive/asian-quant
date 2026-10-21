#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import concurrent.futures

from core.util.decorator import retry
from core.util.func import get_unified_interval
from strategies.moo_strategy import run_strategy
from conf.config import STRATEGY_CONFIG

def calculate_start_date(interval: str, end_day: str) -> tuple[datetime, datetime]:
    end = datetime.strptime(end_day, "%Y-%m-%d")

    if interval == "1m":
        start = end - timedelta(days=6)
    elif interval in ("2m", "5m", "15m", "30m", "90m"):
        start = end - timedelta(days=58)
    elif interval in ("60m", "1h"):
        start = end - timedelta(days=100)
    elif interval == "1wk":
        start = end - timedelta(days=200 * 7)
    elif interval == "1mo":
        start = end - timedelta(days=200 * 7)
    else:
        start = end - timedelta(days=300)

    return start, end

_start, _end = calculate_start_date(
    STRATEGY_CONFIG['UH_INTERVAL'],
    STRATEGY_CONFIG['UH_END_DAY']
)

cache_label = {
    'stocks': 'all',
    'rwa': 'rwa',
    'contract': 'con',
    'hk': 'hke',
}
_cache_path = STRATEGY_CONFIG['UH_CACHE_PATH']
_is_hk = _cache_path == 'hk'

def format_symbol(code: str) -> str:
    if _is_hk:
        stripped = str(int(code))
        if len(stripped) == 5:
            stripped = stripped[1:]
        return f"{stripped.zfill(4)}.HK"
    return code

BASE_DIR = Path(__file__).resolve().parent.parent


CONFIG = {
    "start": _start.strftime("%Y-%m-%d"),
    "end": _end.strftime("%Y-%m-%d"),
    "interval": STRATEGY_CONFIG['UH_INTERVAL'],
    "use_file": True,
    "save_csv": True,
    "file_path": BASE_DIR / f"data/cache/{'hk_stocks' if _cache_path == 'hk' else f'us_{_cache_path}'}_cache.json",
    "output_dir": BASE_DIR / "data/symbols",
    "max_workers": 10
}

def resolve_dates(cfg: dict) -> tuple[str, str]:
    start = datetime.strptime(cfg["start"], "%Y-%m-%d")
    end = datetime.strptime(cfg["end"], "%Y-%m-%d") + timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def load_codes_from_csv(filenames: str | list[str]) -> list[str]:
    if isinstance(filenames, str):
        filenames = [filenames]

    all_codes: list[str] = []
    for filename in filenames:
        name = filename if filename.lower().endswith(".csv") else f"{filename}.csv"
        p = Path(name)
        if not p.is_absolute():
            p = BASE_DIR / "data/cache" / p
        if not p.exists():
            raise FileNotFoundError(f"测试标的文件不存在: {p}")

        try:
            df = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(p, dtype=str, encoding="gbk")

        df.columns = [str(c).strip() for c in df.columns]
        if "代码" not in df.columns:
            raise KeyError(f"{p.name} 中未找到“代码”列，现有列: {list(df.columns)}")

        codes = df["代码"].dropna().astype(str).str.strip()
        all_codes.extend(c for c in codes if c)

    return list(dict.fromkeys(all_codes))

def build_stock_pool(cfg: dict) -> list[dict]:
    if cfg["use_file"]:
        p = Path(cfg["file_path"])
        if not p.exists():
            raise FileNotFoundError(f"股票池文件不存在: {p}")
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        items = raw.get("data", raw) if isinstance(raw, dict) else raw
        print(f"📂 成功读取股票池缓存: {p}")

    elif cfg["use_manual"]:
        items = cfg["manual_list"]
        print(f"✏️  手动列表加载")
    else:
        raise ValueError("请至少开启一个股票池来源")

    pool_filters = STRATEGY_CONFIG.get("MARKET_POOL_FILTERS", {})
    current_filter = pool_filters.get(_cache_path, {})

    check_mic_and_type = current_filter.get("check_mic_and_type", False)
    exclude_kws = [kw.upper() for kw in current_filter.get("exclude_keywords", [])]

    pool = []
    ignored_count = 0

    for item in items:

        code = str(item.get("code", ""))
        name = item.get("name", item.get("description", ""))
        mic = item.get("mic", "")
        stype = item.get("type", "")
        sub_type = item.get("sub_type", "")

        name_upper = name.upper() if name else ""
        code_upper = code.upper()

        if any(kw in name_upper for kw in exclude_kws) or any(kw in code_upper for kw in exclude_kws):
            ignored_count += 1
            continue

        if check_mic_and_type:
            if _is_hk:
                valid_sub_types = current_filter.get("valid_sub_types", [])
                if valid_sub_types and sub_type not in valid_sub_types:
                    ignored_count += 1
                    continue
            else:
                valid_mics = set(current_filter.get("valid_mics", []))
                valid_types = set(current_filter.get("valid_types", []))
                mic_code = mic.split()[0] if mic else ""

                if valid_types and stype not in valid_types:
                    ignored_count += 1
                    continue
                if valid_mics and mic_code not in valid_mics:
                    ignored_count += 1
                    continue
                if "." in code or "-" in code:
                    ignored_count += 1
                    continue

        pool.append({"code": code, "name": name})

    print(f"📋 静态清洗完成！[{_cache_path}] 池共加载 {len(pool)} 只标的 (自适应拦截 {ignored_count} 只非目标股)\n")

    # 优先级：LIST > FILE > N
    test_list = STRATEGY_CONFIG.get("UH_TEST_STOCKS_LIST", [])
    test_file = STRATEGY_CONFIG.get("UH_TEST_STOCKS_FILE", None)
    test_n = STRATEGY_CONFIG.get("UH_TEST_STOCKS", None)

    if test_list:  # 优先：指定标的列表
        test_set = {s.upper() for s in test_list}
        pool = [it for it in pool if it["code"].upper() in test_set]
        print(f"🧪 测试模式 [LIST]：加载 {len(pool)} 只标的  {test_list}\n")
    elif test_file:  # 次优：从 csv 文件导入
        file_codes = load_codes_from_csv(test_file)
        test_set = {s.upper() for s in file_codes}
        pool = [it for it in pool if it["code"].upper() in test_set]
        missing = test_set - {it["code"].upper() for it in pool}
        print(f"🧪 测试模式 [FILE={test_file}]：文件 {len(file_codes)} 个代码，命中 {len(pool)} 只")
        if missing:
            print(f"⚠️ 未在股票池中找到: {sorted(missing)}\n")
    elif test_n is not None:  # 再次：截取前 N 只
        pool = pool[:test_n]
        print(f"🧪 测试模式 [N={test_n}]：截取前 {len(pool)} 只标的\n")

    return pool

@retry(max_retries=2, delay=1)
def run_single(item: dict, start: str, end: str, interval: str) -> list[dict]:
    code, name = item["code"], item["name"]
    symbol = format_symbol(code)
    hits = []
    try:
        df = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )

        if "h" in interval:
            tz = "Asia/Hong_Kong" if _is_hk else "Asia/Shanghai"
            df = df.tz_convert(tz)

        if df.empty or len(df) < 20:
            return hits

        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
        df.columns = pd.Index([c.lower() for c in df.columns])

        for result in run_strategy(df, code):
            result.setdefault("代码", code)
            result["名称"] = name
            result["周期"] = interval.upper()
            hits.append(result)

    except Exception as e:
        print(f" ⚠️  {symbol}: {e}")

    return hits

def scan_signals(pool: list[dict], cfg: dict) -> pd.DataFrame:
    start, end = resolve_dates(cfg)
    interval = cfg["interval"]
    total = len(pool)

    print(
        f"🚀 开始扫描 {total} 只标的"
        f"[{start} ~ {datetime.strptime(cfg['end'], '%Y-%m-%d').strftime('%Y-%m-%d')}]  "
        f"interval={interval}\n"
    )

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg["max_workers"]) as executor:
        future_to_item = {
            executor.submit(run_single, item, start, end, interval): item
            for item in pool
        }

        for i, future in enumerate(concurrent.futures.as_completed(future_to_item), 1):
            item = future_to_item[future]
            try:
                hits = future.result()
                if hits:
                    results.extend(hits)
                    print(f"  [{i:>3}/{total}] ✅  {item['code']}  {item['name']}  ({len(hits)} 个信号)")
                else:
                    print(f"  [{i:>3}/{total}]     {item['code']}  {item['name']}")
            except Exception as e:
                print(f"  [{i:>3}/{total}] ❌  {item['code']}  {item['name']} : {e}")

    if not results:
        print("\n📭 本次扫描无信号")
        return pd.DataFrame()

    return pd.DataFrame(results)

def attach_symbol_info(signals: pd.DataFrame) -> pd.DataFrame:
    market = "hk" if _is_hk else "us"
    cap_col = "市值(亿)"
    p = BASE_DIR / f"data/cache/{market}_all.csv"
    if signals.empty or "代码" not in signals.columns:
        return signals
    if not p.exists():
        print(f"⚠️ 标的信息文件不存在，跳过附加列: {p}")
        return signals

    try:
        info = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        info = pd.read_csv(p, dtype=str, encoding="gbk")
    info.columns = [str(c).strip() for c in info.columns]

    need = ["代码", "市值", "所属行业", "市盈率(静)"]
    miss = [c for c in need if c not in info.columns]
    if miss:
        print(f"⚠️ {p.name} 缺少列 {miss}，现有列: {list(info.columns)}")
        return signals

    def norm(code) -> str:
        s = str(code).strip()
        if _is_hk:
            try:
                return str(int(s.upper().replace(".HK", "")))
            except ValueError:
                return s.upper()
        return s.upper()

    cap = pd.to_numeric(info["市值"].str.replace(",", "", regex=False), errors="coerce")
    info = pd.DataFrame({
        "_key": info["代码"].map(norm),
        cap_col: (cap / 1e8).round(2),
        "所属行业": info["所属行业"],
        "市盈率(静)": info["市盈率(静)"],
    }).drop_duplicates(subset="_key")

    out = signals.copy()
    out["_key"] = out["代码"].map(norm)
    out = out.merge(info, on="_key", how="left").drop(columns="_key")

    new_cols = [cap_col, "所属行业"]
    cols = [c for c in out.columns if c not in new_cols]
    pos = cols.index("名称") + 1 if "名称" in cols else len(cols)
    cols[pos:pos] = new_cols
    return out[cols]

def main():
    pool = build_stock_pool(CONFIG)
    signals = scan_signals(pool, CONFIG)

    if not signals.empty:
        signals = attach_symbol_info(signals)
        print(f"\n🎯 共发现 {len(signals)} 个信号:\n")
        print(signals.to_string(index=False))

        if CONFIG["save_csv"]:
            out_dir = Path(CONFIG["output_dir"])
            date_dir = out_dir / datetime.today().strftime("%Y%m%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            end_str = datetime.strptime(CONFIG['end'], '%Y-%m-%d').strftime('%m%d')
            label = cache_label.get(_cache_path)
            interval_str = get_unified_interval(str(STRATEGY_CONFIG.get("UH_INTERVAL")).lower().strip())
            filename = date_dir / f"{interval_str}_{label}_{end_str}_{datetime.today().strftime('%H:%M:%S')}.csv"
            signals.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"\n💾 已保存: {filename}")

if __name__ == "__main__":
    main()