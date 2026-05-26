import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import Config
from data.database import get_stock_daily, get_broker_data, get_broker_net_summary


def check_break_support(daily_rows, support_price):
    if not daily_rows:
        return False, None
    latest = daily_rows[-1]
    close = latest.get("close")
    if close is None:
        return False, None
    if close < support_price:
        return True, {
            "type": "破線出場",
            "detail": f"收盤價 {close} < 支撐價 {support_price}",
        }
    return False, None


def check_bearish_pattern(daily_rows):
    if len(daily_rows) < 6:
        return False, None
    latest = daily_rows[-1]
    close = latest.get("close")
    open_p = latest.get("open")
    high = latest.get("high") or 0
    vol = latest.get("volume") or 0

    if close is None or open_p is None:
        return False, None

    recent_avg_vol = sum((r.get("volume") or 0) for r in daily_rows[-6:-1]) / 5

    if vol > recent_avg_vol and close < open_p:
        return True, {
            "type": "出量黑K",
            "detail": f"成交量 {vol:,.0f} > 均量 {recent_avg_vol:,.0f}",
        }

    body = abs(close - open_p)
    upper_shadow = high - max(close, open_p)
    if body > 0 and upper_shadow > body:
        return True, {
            "type": "長上影線",
            "detail": f"上影線 {upper_shadow:.2f} > 實體 {body:.2f}",
        }

    return False, None


def check_chip_dump(stock_id, key_broker_id, entry_buy_volume):
    broker_data = get_broker_data(stock_id)
    if not broker_data:
        return False, None

    for row in broker_data:
        if str(row.get("broker_id")) == str(key_broker_id):
            net = row.get("net_volume", 0)
            if net < 0:
                sell_amount = abs(net)
                if entry_buy_volume > 0 and sell_amount / entry_buy_volume >= Config.EXIT_CHIP_DUMP_RATIO:
                    return True, {
                        "type": "籌碼出場",
                        "detail": f"主力 {row.get('broker_name', '')} 單日賣超 {sell_amount} 張",
                    }
    return False, None


def run_exit_check(positions):
    alerts = []

    for pos in positions:
        sid = pos["stock_id"]
        support = pos.get("support_price", 0)
        broker_id = pos.get("key_broker_id")
        entry_buy = pos.get("entry_broker_buy", 0)

        daily = get_stock_daily(sid)
        if not daily:
            continue

        is_break, break_detail = check_break_support(daily, support)
        if Config.EXIT_BREAK_SUPPORT and is_break:
            alerts.append({
                "stock_id": sid,
                "stock_name": pos.get("stock_name", sid),
                "cost_price": pos.get("buy_price"),
                "support_price": support,
                "current_price": daily[-1]["close"],
                "alert_type": break_detail["type"],
                "description": break_detail["detail"],
            })
            continue

        is_pattern, pattern_detail = check_bearish_pattern(daily)
        if Config.EXIT_BEARISH_PATTERN and is_pattern:
            alerts.append({
                "stock_id": sid,
                "stock_name": pos.get("stock_name", sid),
                "cost_price": pos.get("buy_price"),
                "support_price": support,
                "current_price": daily[-1]["close"],
                "alert_type": pattern_detail["type"],
                "description": pattern_detail["detail"],
            })
            continue

        is_dump, dump_detail = check_chip_dump(sid, broker_id, entry_buy)
        if is_dump:
            alerts.append({
                "stock_id": sid,
                "stock_name": pos.get("stock_name", sid),
                "cost_price": pos.get("buy_price"),
                "support_price": support,
                "current_price": daily[-1]["close"],
                "alert_type": dump_detail["type"],
                "description": dump_detail["detail"],
            })

    return alerts
