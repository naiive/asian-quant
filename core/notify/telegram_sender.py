#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import math
import urllib.request
import urllib.parse
from typing import Optional
import pandas as pd

from conf.config import SYSTEM_CONFIG, TELEGRAM_CONFIG
from core.notify.message_builder import build_unified_message

def _http_post_form(url: str, data: dict) -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")

    req = urllib.request.Request(url, data=encoded)

    with urllib.request.urlopen(req, timeout=20) as resp:

        return json.loads(resp.read().decode("utf-8"))

def clip_for_telegram(text: str, limit: int = 3800) -> str:

    return text if len(text) <= limit else text[:limit] + "\n...[截断]"

def send_telegram(
    bot_token: str,
    chat_id: str,
    text: str,
    disable_web_page_preview: bool = True,
    parse_mode: str = "HTML"
) -> bool:
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
            "parse_mode": parse_mode,
        }
        resp = _http_post_form(url, payload)
        if not resp.get("ok"):
            raise RuntimeError(resp)
        print("🤖 [成功] telegram sent")
        return True
    except Exception as e:
        print(f"❌ [失败] telegram failed {e}")
        return False

def telegram_sender(
    df: Optional[pd.DataFrame],
    strategy_name: Optional[str],
    max_rows_per_msg: int = 10
) -> None:

    if isinstance(df, pd.DataFrame) and not df.empty and SYSTEM_CONFIG.get("ENABLE_TELEGRAM"):
        total_cnt = len(df)
        page_cnt = math.ceil(total_cnt / max_rows_per_msg)

        for idx, start in enumerate(range(0, total_cnt, max_rows_per_msg), start=1):
            sub_df = df.iloc[start:start + max_rows_per_msg]
            title_prefix = f"【{strategy_name}】"
            title_main, body = build_unified_message(
                sub_df,
                strategy_name,
                total_cnt=total_cnt,
                page_no=idx,
                page_cnt=page_cnt,
                is_first_page=(idx == 1),
            )
            send_telegram(
                TELEGRAM_CONFIG["TG_TOKEN"],
                str(TELEGRAM_CONFIG["TG_CHAT_ID"]).strip(),
                clip_for_telegram(f"{title_prefix} {title_main}\n\n{body}"),
                TELEGRAM_CONFIG.get("DISABLE_WEB_PAGE_PREVIEW", True)
            )