import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import Config
from data.database import get_stock_daily, get_stock_info


def find_key_red_candle(daily_rows):
    if len(daily_rows) < 2:
        return None

    lookback = min(Config.KEY_CANDLE_LOOKBACK, len(daily_rows) - 1)
    recent = daily_rows[-lookback - 1:-1]

    max_vol = 0
    key_idx = -1

    for i, row in enumerate(recent):
        vol = row.get("volume") or 0
        close = row.get("close")
        open_p = row.get("open")
        if close is None or open_p is None:
            continue
        if close > open_p and vol > max_vol:
            max_vol = vol
            key_idx = len(daily_rows) - lookback - 1 + i

    if key_idx == -1 or max_vol == 0:
        return None

    key_row = daily_rows[key_idx]
    return {
        "date": key_row["date"],
        "open": key_row["open"],
        "high": key_row["high"],
        "low": key_row["low"],
        "close": key_row["close"],
        "volume": max_vol,
        "support_price": key_row["low"],
        "idx": key_idx,
    }


def check_support_held(daily_rows, key_candle):
    if key_candle is None:
        return False
    support = key_candle["support_price"]
    after_key = daily_rows[key_candle["idx"] + 1:]
    for row in after_key:
        if (row.get("close") or 0) < support:
            return False
    return True


def check_bearish_signals(daily_rows, key_candle):
    if key_candle is None:
        return True

    after_key = daily_rows[key_candle["idx"] + 1:]
    if not after_key:
        return False

    recent_avg_vol = sum((r.get("volume") or 0) for r in after_key[-5:]) / min(5, len(after_key))

    for row in after_key:
        vol = row.get("volume") or 0
        close = row.get("close")
        open_p = row.get("open")

        if close is None or open_p is None:
            continue

        if vol > recent_avg_vol and close < open_p:
            return True

        body = abs(close - open_p)
        high = row.get("high") or 0
        upper_shadow = high - max(close, open_p)
        if body > 0 and upper_shadow > body:
            return True

    return False


def run_step2_filter(step1_passed):
    results = []
    excluded = []
    lookback = Config.KEY_CANDLE_LOOKBACK

    for stock in step1_passed:
        sid = stock["stock_id"]
        daily = get_stock_daily(sid)
        if len(daily) < lookback:
            continue

        key_candle = find_key_red_candle(daily)
        if key_candle is None:
            excluded.append({**stock, "reason": "未找到關鍵紅K"})
            continue

        if not check_support_held(daily, key_candle):
            excluded.append({**stock, "reason": "跌破支撐線"})
            continue

        if check_bearish_signals(daily, key_candle):
            excluded.append({**stock, "reason": "出現高檔反轉訊號"})
            continue

        info = get_stock_info(sid)
        results.append({
            **stock,
            "key_candle_date": key_candle["date"],
            "key_candle_volume": key_candle["volume"],
            "support_price": key_candle["support_price"],
            "signal_price": stock["close"],
            "stock_name": info.get("stock_name", sid) if info else sid,
        })

    return {
        "passed": results,
        "excluded": excluded,
        "message": f"通過 {len(results)} 檔，排除 {len(excluded)} 檔",
    }
