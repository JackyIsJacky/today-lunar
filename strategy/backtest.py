import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import Config
from data.database import get_stock_daily, get_stock_info, get_market_daily
from strategy.step1_filter import check_market_volume_contraction, run_step1_filter
from strategy.step2_technical import run_step2_filter
from strategy.step3_chip import run_step3_filter
from strategy.step4_exit import run_exit_check
from trading.simulator import Simulator

import sqlite3
import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market.db")


def _get_backtest_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _run_backtest_blocking(start_date, end_date, capital, trade_ratio, steps, progress_callback=None):
    sim = Simulator()
    sim.reset()

    dates = pd.date_range(start_date, end_date, freq="B")
    total = len(dates)
    trades = []
    equity_curve = []
    market_curve = []

    for i, dt in enumerate(dates):
        date_str = dt.strftime("%Y-%m-%d")

        if progress_callback:
            progress_callback(i + 1, total)

        try:
            # step 1: get market data and run filter
            # For backtest, we use DB data for the given date
            # This is simplified - in production, we'd run per-day

            # step 4: check exit signals for existing positions
            positions = sim.get_positions()
            if positions:
                alerts = run_exit_check(positions)
                for alert in alerts:
                    sid = alert["stock_id"]
                    price = alert.get("current_price", 0)
                    sim.sell_all(sid, price, alert.get("description", ""))

        except Exception:
            continue

        # equity tracking
        summary = sim.get_portfolio_summary()
        equity_curve.append({
            "date": date_str,
            "equity": summary["total_asset"],
        })

    account = sim.get_account()
    trades = sim.get_trade_history(1000)
    summary = sim.get_portfolio_summary()

    # compute metrics
    equity_values = [e["equity"] for e in equity_curve]
    returns = []
    for i in range(1, len(equity_values)):
        if equity_values[i - 1] > 0:
            returns.append((equity_values[i] - equity_values[i - 1]) / equity_values[i - 1])

    total_return = (equity_values[-1] - capital) / capital * 100 if equity_values else 0
    annual_return = total_return / (total / 252) if total > 0 else 0
    win_count = sum(1 for t in trades if t.get("direction") == "sell" and (t.get("pnl") or 0) > 0)
    total_sells = sum(1 for t in trades if t.get("direction") == "sell")
    win_rate = win_count / total_sells * 100 if total_sells > 0 else 0

    # max drawdown
    peak = equity_values[0] if equity_values else capital
    mdd = 0
    for v in equity_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > mdd:
            mdd = dd

    # sharpe ratio
    if returns:
        avg_ret = np.mean(returns)
        std_ret = np.std(returns)
        sharpe = (avg_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0
    else:
        sharpe = 0

    return {
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(mdd, 2),
        "sharpe": round(sharpe, 2),
        "trade_count": total_sells,
        "trades": [dict(t) for t in trades[-50:]],
        "equity_curve": equity_curve,
    }


def run_backtest_sync(start_date, end_date, capital, trade_ratio, steps):
    """Simple sync entry point for direct call"""
    return _run_backtest_blocking(start_date, end_date, capital, trade_ratio, steps)
