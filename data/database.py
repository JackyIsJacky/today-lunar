import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY DEFAULT 1,
            initial_capital REAL,
            cash REAL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS market_daily (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            turnover REAL,
            volume_ma5 REAL,
            volume_ma20 REAL
        );

        CREATE TABLE IF NOT EXISTS stock_daily (
            stock_id TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            turnover REAL,
            PRIMARY KEY (stock_id, date)
        );

        CREATE TABLE IF NOT EXISTS stock_info (
            stock_id TEXT PRIMARY KEY,
            stock_name TEXT,
            industry TEXT,
            capital REAL,
            listing_date TEXT
        );

        CREATE TABLE IF NOT EXISTS broker_buy_sell (
            stock_id TEXT,
            date TEXT,
            broker_id TEXT,
            broker_name TEXT,
            buy_volume REAL,
            sell_volume REAL,
            net_volume REAL,
            PRIMARY KEY (stock_id, date, broker_id)
        );

        CREATE TABLE IF NOT EXISTS screening_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            step INTEGER,
            stock_id TEXT,
            stock_name TEXT,
            detail TEXT
        );

        CREATE TABLE IF NOT EXISTS trade_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            stock_id TEXT,
            stock_name TEXT,
            direction TEXT,
            price REAL,
            reason TEXT,
            step INTEGER
        );

        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id TEXT,
            stock_name TEXT,
            buy_date TEXT,
            buy_price REAL,
            shares INTEGER,
            support_price REAL,
            key_broker_id TEXT,
            key_broker_name TEXT,
            entry_reason TEXT,
            status TEXT DEFAULT 'holding'
        );

        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            stock_id TEXT,
            stock_name TEXT,
            direction TEXT,
            shares INTEGER,
            price REAL,
            reason TEXT,
            pnl REAL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    conn.commit()
    conn.close()

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM account")
    if c.fetchone()["n"] == 0:
        c.execute("INSERT INTO account (initial_capital, cash, created_at) VALUES (?, ?, ?)",
                  (1000000.0, 1000000.0, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def upsert_market_daily(df_dict, conn=None):
    close_conn = False
    if conn is None:
        conn = get_conn()
        close_conn = True
    c = conn.cursor()
    for row in df_dict:
        c.execute("""
            INSERT OR REPLACE INTO market_daily (date, open, high, low, close, volume, turnover, volume_ma5, volume_ma20)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(row["date"])[:10],
            row["open"], row["high"], row["low"], row["close"],
            row["volume"], row.get("turnover", 0),
            row.get("volume_ma5"), row.get("volume_ma20"),
        ))
    conn.commit()
    if close_conn:
        conn.close()


def upsert_stock_daily(stock_id, df_dict, conn=None):
    close_conn = False
    if conn is None:
        conn = get_conn()
        close_conn = True
    c = conn.cursor()
    for row in df_dict:
        c.execute("""
            INSERT OR REPLACE INTO stock_daily (stock_id, date, open, high, low, close, volume, turnover)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stock_id, str(row["date"])[:10],
            row["open"], row["high"], row["low"], row["close"],
            row["volume"], row.get("turnover", 0),
        ))
    conn.commit()
    if close_conn:
        conn.close()


def upsert_stock_info(info, conn=None):
    close_conn = False
    if conn is None:
        conn = get_conn()
        close_conn = True
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO stock_info (stock_id, stock_name, industry, capital, listing_date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        info["stock_id"], info.get("stock_name", ""), info.get("industry", ""),
        info.get("capital"), info.get("listing_date"),
    ))
    conn.commit()
    if close_conn:
        conn.close()


def upsert_broker_data(rows, conn=None):
    close_conn = False
    if conn is None:
        conn = get_conn()
        close_conn = True
    c = conn.cursor()
    for row in rows:
        c.execute("""
            INSERT OR REPLACE INTO broker_buy_sell (stock_id, date, broker_id, broker_name, buy_volume, sell_volume, net_volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            row["stock_id"], str(row["date"])[:10], str(row["broker_id"]),
            row.get("broker_name", ""), row.get("buy", 0), row.get("sell", 0),
            row.get("net", 0),
        ))
    conn.commit()
    if close_conn:
        conn.close()


def get_market_daily(date=None):
    conn = get_conn()
    c = conn.cursor()
    if date:
        c.execute("SELECT * FROM market_daily WHERE date = ?", (date,))
    else:
        c.execute("SELECT * FROM market_daily ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stock_daily(stock_id, start_date=None, end_date=None):
    conn = get_conn()
    c = conn.cursor()
    query = "SELECT * FROM stock_daily WHERE stock_id = ?"
    params = [stock_id]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date ASC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_stock_ids():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT stock_id FROM stock_daily")
    rows = c.fetchall()
    conn.close()
    return [r["stock_id"] for r in rows]


def get_stock_info(stock_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM stock_info WHERE stock_id = ?", (stock_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_settings():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM settings")
    rows = c.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def save_settings(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def save_screening_result(run_date, step, stock_id, stock_name, detail):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO screening_results (run_date, step, stock_id, stock_name, detail)
        VALUES (?, ?, ?, ?, ?)
    """, (run_date, step, stock_id, stock_name, detail))
    conn.commit()
    conn.close()


def get_latest_screening(step=None):
    conn = get_conn()
    c = conn.cursor()
    if step:
        c.execute("""
            SELECT * FROM screening_results WHERE run_date = (
                SELECT MAX(run_date) FROM screening_results WHERE step = ?
            ) AND step = ?
        """, (step, step))
    else:
        c.execute("""
            SELECT * FROM screening_results WHERE run_date = (
                SELECT MAX(run_date) FROM screening_results
            )
        """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_trade_signal(date, stock_id, stock_name, direction, price, reason, step):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO trade_signals (date, stock_id, stock_name, direction, price, reason, step)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (date, stock_id, stock_name, direction, price, reason, step))
    conn.commit()
    conn.close()


def get_trade_signals(limit=10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM trade_signals ORDER BY date DESC, id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_broker_data(stock_id, start_date=None, end_date=None):
    conn = get_conn()
    c = conn.cursor()
    query = "SELECT * FROM broker_buy_sell WHERE stock_id = ?"
    params = [stock_id]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date DESC, net_volume DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_broker_net_summary(stock_id, start_date=None, end_date=None):
    conn = get_conn()
    c = conn.cursor()
    query = """
        SELECT broker_id, broker_name,
               SUM(buy_volume) as total_buy,
               SUM(sell_volume) as total_sell,
               SUM(net_volume) as total_net,
               COUNT(DISTINCT date) as days_count
        FROM broker_buy_sell WHERE stock_id = ?
    """
    params = [stock_id]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " GROUP BY broker_id ORDER BY total_net DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


__all__ = [
    "init_db", "get_conn",
    "upsert_market_daily", "upsert_stock_daily", "upsert_stock_info", "upsert_broker_data",
    "get_market_daily", "get_stock_daily", "get_all_stock_ids", "get_stock_info",
    "get_settings", "save_settings",
    "save_screening_result", "get_latest_screening",
    "save_trade_signal", "get_trade_signals",
    "get_broker_data", "get_broker_net_summary",
]
