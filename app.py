import json
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template, request

from config import Config
from data.database import (
    get_all_stock_ids,
    get_latest_screening,
    get_stock_daily,
    get_stock_info,
    get_trade_signals,
    get_broker_net_summary,
    init_db,
    save_screening_result,
    upsert_market_daily,
    upsert_stock_daily,
    upsert_stock_info,
    get_market_daily,
)
from data.fetcher import fetcher
from strategy.step1_filter import run_step1_filter, check_market_volume_contraction
from strategy.step2_technical import run_step2_filter
from strategy.step3_chip import run_step3_filter
from strategy.step4_exit import run_exit_check
from strategy.backtest import run_backtest_sync
from trading.simulator import simulator
from utils.device import detect_device

app = Flask(__name__)
app.config.from_object(Config)

scheduler = BackgroundScheduler()
scheduler.start()

init_db()
detect_device()

# ---------- global state ----------
_init_progress = {"status": "idle", "message": "", "current": 0, "total": 0}
_stock_list_cache = None
_backtest_running = False
_backtest_result = None


def load_stock_list():
    global _stock_list_cache
    try:
        df = fetcher.fetch_stock_list()
        _stock_list_cache = df
        cids = df["stock_id"].unique().tolist()
        cids = [s for s in cids if len(str(s)) == 4 and str(s).isdigit()]
        print(f"[DATA] Stock list: {len(cids)} stocks loaded")
        return cids
    except Exception as e:
        print(f"[DATA] Stock list failed: {e}")
        return []


def update_market_data():
    try:
        df = fetcher.fetch_taiwan_index()
        if df.empty:
            return 0
        df["volume_ma5"] = df["volume"].rolling(5).mean()
        df["volume_ma20"] = df["volume"].rolling(20).mean()
        upsert_market_daily(df.to_dict(orient="records"))
        print(f"[DATA] Market: {len(df)} rows")
        return len(df)
    except Exception as e:
        print(f"[DATA] Market failed: {e}")
        return 0


def update_all_stocks_daily():
    ids = get_all_stock_ids()
    if not ids:
        return 0
    cnt = 0
    for sid in ids[:300]:
        try:
            df = fetcher.fetch_stock_daily(sid)
            if df.empty:
                continue
            upsert_stock_daily(sid, df.to_dict(orient="records"))
            cnt += 1
        except Exception:
            pass
    print(f"[DATA] Stocks daily: {cnt} updated")
    return cnt


def initial_stock_load(stock_ids, limit=None):
    global _init_progress
    _init_progress = {"status": "running", "message": "Initializing stock data...", "current": 0, "total": len(stock_ids)}

    ids = stock_ids[:limit] if limit else stock_ids
    cnt = 0
    for i, sid in enumerate(ids):
        try:
            daily = fetcher.fetch_stock_daily(sid)
            if not daily.empty:
                upsert_stock_daily(sid, daily.to_dict(orient="records"))
            info_row = fetcher.fetch_stock_basic_info(sid)
            if info_row:
                upsert_stock_info(info_row)
            cnt += 1
            if cnt % 50 == 0:
                _init_progress = {"status": "running", "message": f"Loading {cnt}/{len(ids)}", "current": cnt, "total": len(ids)}
                print(f"[DATA] Progress: {cnt}/{len(ids)}")
        except Exception as e:
            pass

    _init_progress = {"status": "done", "message": f"Complete: {cnt} stocks", "current": cnt, "total": len(ids)}
    print(f"[DATA] Initial load: {cnt} stocks")
    return cnt


# ---------- scheduler ----------
@scheduler.scheduled_job("cron", hour=14, minute=30, id="daily_market_update")
def scheduled_market_update():
    update_market_data()


@scheduler.scheduled_job("cron", hour=15, minute=0, id="daily_stock_update")
def scheduled_stock_update():
    update_all_stocks_daily()


# ---------- API ----------
@app.route("/api/status")
def api_status():
    return jsonify({
        "status": "ok",
        "version": "0.2.0",
        "token_set": bool(Config.FINMIND_TOKEN),
        "init_progress": _init_progress,
    })


@app.route("/api/init", methods=["POST"])
def api_init():
    global _init_progress
    data = request.json if request.is_json else {}
    count = data.get("count", 50)

    def _run():
        ids = load_stock_list()
        if ids:
            update_market_data()
            initial_stock_load(ids, count)

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/init_progress")
def api_init_progress():
    return jsonify(_init_progress)


@app.route("/api/dashboard")
def api_dashboard():
    market_status = check_market_volume_contraction()
    screening = {1: [], 2: [], 3: []}
    for step in [1, 2, 3]:
        rows = get_latest_screening(step)
        screening[step] = [dict(r) for r in rows]
    signals = [dict(r) for r in get_trade_signals(10)]

    return jsonify({
        "market": market_status,
        "step1_count": len(screening[1]),
        "step2_count": len(screening[2]),
        "step3_count": len(screening[3]),
        "signals": signals,
    })


@app.route("/api/run_screening", methods=["POST"])
def api_run_screening():
    step = request.json.get("step", 0) if request.is_json else 0
    run_date = datetime.now().strftime("%Y-%m-%d")
    results = {}

    if step == 0 or step == 1:
        r1 = run_step1_filter()
        results["step1"] = {
            "market_status": r1["market_status"],
            "count": len(r1["passed"]),
            "passed": r1["passed"],
            "message": r1["message"],
        }
        for item in r1["passed"]:
            save_screening_result(run_date, 1, item["stock_id"], item.get("stock_name", ""),
                                  json.dumps(item, ensure_ascii=False, default=str))

    if step == 0 or step == 2:
        step1_data = results.get("step1", {}).get("passed", [])
        if step == 2 and not step1_data:
            step1_data = run_step1_filter()["passed"]
        r2 = run_step2_filter(step1_data)
        results["step2"] = {
            "count": len(r2["passed"]),
            "passed": r2["passed"],
            "excluded": r2["excluded"],
            "message": r2["message"],
        }
        for item in r2["passed"]:
            save_screening_result(run_date, 2, item["stock_id"], item.get("stock_name", ""),
                                  json.dumps(item, ensure_ascii=False, default=str))

    if step == 0 or step == 3:
        step2_data = results.get("step2", {}).get("passed", [])
        if step == 3 and not step2_data:
            step2_data = run_step2_filter(run_step1_filter()["passed"])["passed"]
        r3 = run_step3_filter(step2_data)
        results["step3"] = {
            "count": len(r3["passed"]),
            "passed": r3["passed"],
            "excluded": r3["excluded"],
            "message": r3["message"],
        }
        for item in r3["passed"]:
            save_screening_result(run_date, 3, item["stock_id"], item.get("stock_name", ""),
                                  json.dumps(item, ensure_ascii=False, default=str))

    return jsonify(results)


@app.route("/api/stock/<stock_id>")
def api_stock_detail(stock_id):
    info = get_stock_info(stock_id)
    daily = get_stock_daily(stock_id)
    brokers = get_broker_net_summary(stock_id)

    kline = []
    for r in daily[-200:]:
        kline.append({
            "time": r["date"],
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["volume"],
        })

    return jsonify({
        "stock_id": stock_id,
        "stock_name": info.get("stock_name", stock_id) if info else stock_id,
        "info": info,
        "kline": kline,
        "brokers": [dict(b) for b in brokers[:10]],
    })


@app.route("/api/update_data", methods=["POST"])
def api_update_data():
    data_type = request.json.get("type", "market") if request.is_json else "market"
    try:
        if data_type == "market":
            n = update_market_data()
        elif data_type == "stocks":
            n = update_all_stocks_daily()
        else:
            n = update_market_data()
            update_all_stocks_daily()
        return jsonify({"status": "ok", "count": n})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------- pages ----------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/screening")
def screening():
    return render_template("screening.html")


@app.route("/stock/<stock_id>")
def stock_detail(stock_id):
    return render_template("stock_detail.html", stock_id=stock_id)


@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")


@app.route("/backtest")
def backtest():
    return render_template("backtest.html")


@app.route("/settings")
def settings():
    return render_template("settings.html")


# ---------- portfolio API ----------
@app.route("/api/portfolio/summary")
def api_portfolio_summary():
    summary = simulator.get_portfolio_summary()
    return jsonify(summary)


@app.route("/api/portfolio/positions")
def api_portfolio_positions():
    positions = simulator.get_positions()
    result = []
    for pos in positions:
        daily = get_stock_daily(pos["stock_id"])
        current_price = pos["buy_price"]
        if daily:
            current_price = daily[-1].get("close", pos["buy_price"])
        pnl_pct = (current_price - pos["buy_price"]) / pos["buy_price"] * 100 if pos["buy_price"] > 0 else 0
        result.append({
            **pos,
            "current_price": current_price,
            "pnl_pct": round(pnl_pct, 2),
        })
    return jsonify(result)


@app.route("/api/portfolio/buy", methods=["POST"])
def api_portfolio_buy():
    data = request.json if request.is_json else {}
    res = simulator.buy(
        stock_id=data.get("stock_id", ""),
        stock_name=data.get("stock_name", ""),
        price=data.get("price", 0),
        shares=data.get("shares", 1),
        support_price=data.get("support_price", 0),
        broker_id=data.get("broker_id", ""),
        broker_name=data.get("broker_name", ""),
        reason=data.get("reason", ""),
    )
    return jsonify(res)


@app.route("/api/portfolio/sell", methods=["POST"])
def api_portfolio_sell():
    data = request.json if request.is_json else {}
    position_id = data.get("position_id")
    price = data.get("price", 0)
    reason = data.get("reason", "")

    if position_id == "all" or position_id == -1:
        positions = simulator.get_positions()
        all_results = []
        for pos in positions:
            sid = pos["stock_id"]
            if not price:
                daily = get_stock_daily(sid)
                sell_price = daily[-1].get("close", pos["buy_price"]) if daily else pos["buy_price"]
            else:
                sell_price = price
            res = simulator.sell(pos["id"], sell_price, reason)
            all_results.append(res)
        return jsonify({"results": all_results})
    else:
        res = simulator.sell(position_id, price, reason)
        return jsonify(res)


@app.route("/api/portfolio/reset", methods=["POST"])
def api_portfolio_reset():
    res = simulator.reset()
    return jsonify(res)


@app.route("/api/portfolio/history")
def api_portfolio_history():
    history = simulator.get_trade_history(50)
    return jsonify(history)


@app.route("/api/portfolio/exit_alerts")
def api_portfolio_exit_alerts():
    positions = simulator.get_positions()
    if not positions:
        return jsonify([])
    alerts = run_exit_check(positions)
    return jsonify(alerts)


# ---------- backtest API ----------
@app.route("/api/backtest/run", methods=["POST"])
def api_backtest_run():
    global _backtest_result, _backtest_running

    data = request.json if request.is_json else {}
    start_date = data.get("start_date", "2024-01-01")
    end_date = data.get("end_date", "2024-12-31")
    capital = float(data.get("capital", Config.INITIAL_CAPITAL))
    trade_ratio = float(data.get("trade_ratio", Config.TRADE_RATIO))
    steps = data.get("steps", [1, 2, 3, 4])

    def _do():
        global _backtest_result, _backtest_running
        try:
            result = run_backtest_sync(start_date, end_date, capital, trade_ratio, steps)
            _backtest_result = result
        except Exception as e:
            _backtest_result = {"error": str(e)}
        finally:
            _backtest_running = False

    _backtest_result = None
    _backtest_running = True

    threading.Thread(target=_do, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/backtest/status")
def api_backtest_status():
    global _backtest_result, _backtest_running
    if _backtest_running:
        return jsonify({"status": "running"})
    if _backtest_result:
        return jsonify({"status": "done", "result": _backtest_result})
    return jsonify({"status": "idle"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=app.config["FLASK_PORT"],
        debug=app.config["FLASK_DEBUG"],
    )
