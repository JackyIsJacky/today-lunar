import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DEVICE = os.getenv("DEVICE", "auto")
    FINMIND_TOKEN = os.getenv("FINMIND_TOKEN", "")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    INITIAL_CAPITAL = 1_000_000
    TRADE_RATIO = 0.2
    COMMISSION_RATE = 0.001425
    TAX_RATE = 0.003

    CAPITAL_THRESHOLD = 1_000_000_000
    PRICE_THRESHOLD = 50

    KEY_CANDLE_LOOKBACK = 20
    CHIP_LOOKBACK_DAYS = 5
    CHIP_TOP_N = 5

    MA_PERIODS = [5, 20, 60, 120]
    VOLUME_MA_PERIOD = 5

    DAYTRADE_BROKERS = ["9200", "9600", "9868"]

    EXIT_BREAK_SUPPORT = True
    EXIT_BEARISH_PATTERN = True
    EXIT_CHIP_DUMP_RATIO = 0.3
