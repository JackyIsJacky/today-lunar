import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import Config
from data.database import get_broker_data, get_broker_net_summary, get_stock_daily


def check_consecutive_buying(broker_net, days=5):
    if not broker_net:
        return False, None

    top_brokers = [b for b in broker_net if b.get("total_net", 0) > 0]
    if not top_brokers:
        return False, None

    best = top_brokers[0]
    consecutive_days = best.get("days_count", 0)

    return consecutive_days >= 3, best


def check_daytrade_concentration(broker_data, daytrade_list):
    if not broker_data:
        return False

    today_data = [r for r in broker_data if r.get("net_volume", 0) > 0]
    if not today_data:
        return False

    top1 = today_data[0]
    top1_broker = str(top1.get("broker_id", ""))

    if top1_broker in daytrade_list:
        if len(today_data) >= 3:
            second_third_sum = sum(r.get("net_volume", 0) for r in today_data[1:3])
            if top1.get("net_volume", 0) > second_third_sum * 2:
                return True

    return False


def find_dip_buyer(stock_id, broker_data):
    daily = get_stock_daily(stock_id)
    if len(daily) < 60:
        return None

    df = pd.DataFrame(daily)
    df["close"] = pd.to_numeric(df["close"])
    df["pct_change"] = df["close"].pct_change()
    df["drawdown"] = (df["close"] - df["close"].cummax()) / df["close"].cummax()

    crash_periods = df[df["drawdown"] < -0.15]
    if crash_periods.empty:
        return None

    crash_start = crash_periods.iloc[0]["date"]
    crash_end = crash_periods.iloc[-1]["date"]

    broker_net = get_broker_net_summary(stock_id, crash_start, crash_end)
    if not broker_net:
        return None

    dip_buyer = broker_net[0]
    if dip_buyer.get("total_net", 0) <= 0:
        return None

    recent_start = crash_end
    recent_end = datetime.now().strftime("%Y-%m-%d")
    recent_net = get_broker_net_summary(stock_id, recent_start, recent_end)

    broker_sell = sum(
        r.get("total_sell", 0)
        for r in recent_net
        if str(r.get("broker_id")) == str(dip_buyer.get("broker_id"))
    ) if recent_net else 0

    total_buy = dip_buyer.get("total_buy", 1)
    sell_ratio = broker_sell / total_buy if total_buy > 0 else 1.0

    if sell_ratio < 0.3:
        return {
            "broker_id": dip_buyer["broker_id"],
            "broker_name": dip_buyer.get("broker_name", ""),
            "crash_buy": dip_buyer["total_net"],
            "recent_sell": broker_sell,
            "sell_ratio": round(sell_ratio, 2),
            "crash_start": crash_start,
            "crash_end": crash_end,
        }

    return None


def run_step3_filter(step2_passed):
    results = []
    excluded = []
    daytrade_list = Config.DAYTRADE_BROKERS

    for stock in step2_passed:
        sid = stock["stock_id"]
        broker_data = get_broker_data(sid)
        broker_net = get_broker_net_summary(sid)

        has_consecutive, best_broker = check_consecutive_buying(broker_net, Config.CHIP_LOOKBACK_DAYS)
        if not has_consecutive:
            excluded.append({**stock, "reason": "無連續買盤"})
            continue

        is_daytrade = check_daytrade_concentration(broker_data, daytrade_list)
        if is_daytrade:
            excluded.append({**stock, "reason": f"隔日衝干擾 ({best_broker.get('broker_name', '')})"})

        dip_signal = find_dip_buyer(sid, broker_data)

        results.append({
            **stock,
            "broker_id": best_broker["broker_id"],
            "broker_name": best_broker.get("broker_name", ""),
            "consecutive_days": best_broker.get("days_count", 0),
            "total_net_buy": best_broker.get("total_net", 0),
            "daytrade_warning": is_daytrade,
            "dip_signal": dip_signal,
        })

    return {
        "passed": results,
        "excluded": excluded,
        "message": f"通過 {len(results)} 檔，排除 {len(excluded)} 檔",
    }
