import time
import pandas as pd
from FinMind.data import DataLoader

from config import Config


class Fetcher:
    def __init__(self):
        self.api = DataLoader()
        self.api.login_by_token(api_token=Config.FINMIND_TOKEN)

    def fetch_taiwan_index(self, start_date="2023-01-01") -> pd.DataFrame:
        df = self.api.taiwan_stock_daily(
            stock_id="TAIEX",
            start_date=start_date,
        )
        if df.empty:
            return df
        df = df.rename(columns={
            "date": "date",
            "open": "open",
            "max": "high",
            "min": "low",
            "close": "close",
            "Trading_Volume": "volume",
            "Trading_money": "turnover",
        })
        df = df[["date", "open", "high", "low", "close", "volume", "turnover"]]
        df["volume"] = df["volume"].astype(float)
        return df

    def fetch_stock_list(self) -> pd.DataFrame:
        df = self.api.taiwan_stock_info()
        return df

    def fetch_stock_daily(self, stock_id: str, start_date="2023-01-01") -> pd.DataFrame:
        time.sleep(0.3)
        df = self.api.taiwan_stock_daily(
            stock_id=stock_id,
            start_date=start_date,
        )
        if df.empty:
            return df
        df = df.rename(columns={
            "date": "date",
            "open": "open",
            "max": "high",
            "min": "low",
            "close": "close",
            "Trading_Volume": "volume",
            "Trading_money": "turnover",
        })
        df = df[["date", "open", "high", "low", "close", "volume", "turnover"]]
        df["volume"] = df["volume"].astype(float)
        return df

    def fetch_stock_basic_info(self, stock_id: str):
        time.sleep(0.2)
        df = self.api.taiwan_stock_info(stock_id=stock_id)
        if df.empty:
            return None
        row = df.iloc[0]
        return {
            "stock_id": stock_id,
            "stock_name": row.get("stock_name", ""),
            "industry": row.get("industry_category", ""),
        }

    def fetch_stock_capital(self, stock_id: str):
        time.sleep(0.2)
        df = self.api.taiwan_stock_per_pbr(
            stock_id=stock_id,
            start_date="2023-01-01",
        )
        return df

    def fetch_broker_buy_sell(self, stock_id: str, date: str):
        time.sleep(0.3)
        df = self.api.taiwan_stock_broker_buy_sell(
            stock_id=stock_id,
            start_date=date,
            end_date=date,
        )
        return df

    def fetch_broker_buy_sell_range(self, stock_id: str, start_date: str, end_date: str):
        time.sleep(0.3)
        df = self.api.taiwan_stock_broker_buy_sell(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )
        return df

    def fetch_taiwan_margin(self, stock_id: str, start_date="2023-01-01"):
        time.sleep(0.2)
        df = self.api.taiwan_stock_margin_purchase_short_sale(
            stock_id=stock_id,
            start_date=start_date,
        )
        return df


fetcher = Fetcher()
