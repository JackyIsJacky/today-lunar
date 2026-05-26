import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import Config
from data.database import get_market_daily, get_all_stock_ids, get_stock_daily, get_stock_info


def check_market_volume_contraction():
    rows = get_market_daily()
    if len(rows) < Config.VOLUME_MA_PERIOD + 1:
        return {"status": "insufficient_data", "today_volume": 0, "volume_ma": 0}

    rows_sorted = sorted(rows, key=lambda x: x["date"])
    today = rows_sorted[-1]
    recent = rows_sorted[-(Config.VOLUME_MA_PERIOD + 1):-1]

    today_vol = today["volume"] or 0
    avg_vol = sum(r["volume"] or 0 for r in recent) / len(recent) if recent else today_vol

    is_contraction = today_vol < avg_vol

    return {
        "status": "contraction" if is_contraction else "expansion",
        "date": today["date"],
        "index_close": today["close"],
        "today_volume": today_vol,
        "volume_ma": round(avg_vol, 2),
        "is_contraction": is_contraction,
    }


def run_step1_filter():
    market_status = check_market_volume_contraction()
    results = []

    if not market_status["is_contraction"]:
        return {
            "market_status": market_status,
            "passed": [],
            "total_checked": 0,
            "message": "大盤未量縮，跳過選股",
        }

    stock_ids = get_all_stock_ids()
    total_checked = 0

    for sid in stock_ids:
        total_checked += 1
        info = get_stock_info(sid)
        daily = get_stock_daily(sid)
        if not daily:
            continue

        latest = daily[-1]

        capital = info.get("capital") if info else None
        if capital is not None and capital > Config.CAPITAL_THRESHOLD:
            continue

        close_price = latest.get("close")
        if close_price is None or close_price >= Config.PRICE_THRESHOLD:
            continue

        capital_display = f"{(capital / 1e8):.1f} 億" if capital else "N/A"
        results.append({
            "stock_id": sid,
            "stock_name": info.get("stock_name", sid) if info else sid,
            "close": close_price,
            "capital": capital_display,
            "volume": latest.get("volume", 0),
        })

    return {
        "market_status": market_status,
        "passed": results,
        "total_checked": total_checked,
        "message": f"通過 {len(results)} 檔",
    }
