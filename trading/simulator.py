import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class Simulator:
    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        from data.database import init_db
        init_db()

    def get_account(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM account WHERE id = 1")
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_positions(self):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM positions WHERE status = 'holding' ORDER BY buy_date DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_trade_history(self, limit=50):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM trade_history ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def buy(self, stock_id, stock_name, price, shares, support_price=0,
            broker_id="", broker_name="", reason=""):
        conn = get_conn()
        c = conn.cursor()

        c.execute("SELECT cash FROM account WHERE id = 1")
        cash = c.fetchone()["cash"]
        cost = price * shares * 1000
        commission = max(cost * 0.001425, 20)

        total = cost + commission
        if total > cash:
            max_shares = int((cash - 20) / (price * 1000 * 1.001425))
            if max_shares <= 0:
                conn.close()
                return {"success": False, "message": "資金不足"}
            shares = max_shares
            cost = price * shares * 1000
            commission = max(cost * 0.001425, 20)
            total = cost + commission

        c.execute("UPDATE account SET cash = cash - ?", (total,))

        c.execute("""
            INSERT INTO positions (stock_id, stock_name, buy_date, buy_price, shares,
                                   support_price, key_broker_id, key_broker_name, entry_reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'holding')
        """, (stock_id, stock_name, datetime.now().strftime("%Y-%m-%d"),
              price, shares, support_price, broker_id, broker_name, reason))

        c.execute("""
            INSERT INTO trade_history (date, stock_id, stock_name, direction, shares, price, reason)
            VALUES (?, ?, ?, 'buy', ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d"), stock_id, stock_name, shares, price, reason))

        conn.commit()
        conn.close()
        return {"success": True, "message": f"買入 {stock_name} {shares} 張 @ {price}"}

    def sell(self, position_id, price, reason=""):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM positions WHERE id = ? AND status = 'holding'", (position_id,))
        pos = c.fetchone()
        if not pos:
            conn.close()
            return {"success": False, "message": "找不到該庫存"}

        pos = dict(pos)
        revenue = price * pos["shares"] * 1000
        commission = max(revenue * 0.001425, 20)
        tax = revenue * 0.003
        net_revenue = revenue - commission - tax

        cost = pos["buy_price"] * pos["shares"] * 1000
        buy_commission = max(cost * 0.001425, 20)
        pnl = net_revenue - cost - buy_commission

        c.execute("UPDATE account SET cash = cash + ?", (net_revenue,))
        c.execute("UPDATE positions SET status = 'closed' WHERE id = ?", (position_id,))
        c.execute("""
            INSERT INTO trade_history (date, stock_id, stock_name, direction, shares, price, reason, pnl)
            VALUES (?, ?, ?, 'sell', ?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d"), pos["stock_id"], pos["stock_name"],
              pos["shares"], price, reason, round(pnl, 2)))

        conn.commit()
        conn.close()
        return {"success": True, "message": f"賣出 {pos['stock_name']} {pos['shares']} 張, 損益 {pnl:,.0f}"}

    def sell_all(self, stock_id, price, reason=""):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM positions WHERE stock_id = ? AND status = 'holding'", (stock_id,))
        results = []
        for row in c.fetchall():
            pos = dict(row)
            res = self.sell(pos["id"], price, reason)
            results.append(res)
        return results

    def sell_alert_positions(self, alerts, current_prices):
        results = []
        for alert in alerts:
            sid = alert["stock_id"]
            price = current_prices.get(sid, alert.get("current_price", 0))
            reasons = self.sell_all(sid, price, alert.get("description", "出場訊號"))
            results.extend(reasons)
        return results

    def get_portfolio_summary(self):
        from data.database import get_stock_daily

        account = self.get_account()
        positions = self.get_positions()

        total_market_value = 0
        total_cost = 0
        for pos in positions:
            daily = get_stock_daily(pos["stock_id"])
            current_price = pos["buy_price"]
            if daily:
                current_price = daily[-1].get("close", pos["buy_price"])
            total_market_value += current_price * pos["shares"] * 1000
            total_cost += pos["buy_price"] * pos["shares"] * 1000

        cash = account.get("cash", 0) if account else 0
        init_cap = account.get("initial_capital", 1_000_000) if account else 1_000_000
        total_asset = cash + total_market_value
        unrealized_pnl = total_market_value - total_cost

        win_count = 0
        total_count = 0
        history = self.get_trade_history(1000)
        for h in history:
            if h["direction"] == "sell" and h["pnl"] is not None:
                total_count += 1
                if h["pnl"] > 0:
                    win_count += 1

        return {
            "initial_capital": init_cap,
            "cash": cash,
            "total_market_value": total_market_value,
            "total_asset": total_asset,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_asset - init_cap,
            "total_return": round((total_asset - init_cap) / init_cap * 100, 2) if init_cap > 0 else 0,
            "win_rate": round(win_count / total_count * 100, 2) if total_count > 0 else 0,
            "position_count": len(positions),
            "trade_count": total_count,
        }

    def reset(self):
        from config import Config
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM positions")
        c.execute("DELETE FROM trade_history")
        c.execute("UPDATE account SET cash = ?, initial_capital = ?", (Config.INITIAL_CAPITAL, Config.INITIAL_CAPITAL))
        conn.commit()
        conn.close()
        return {"success": True}


simulator = Simulator()
