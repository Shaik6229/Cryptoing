import os
import logging

# ================================================================
# LOGGING SETUP
# ================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("CryptoBot4H")

# ================================================================
# ENVIRONMENT & EXECUTION MODE
# ================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

RUN_MODE = os.environ.get(
    "BOT_RUN_MODE",
    os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch")
)

# ================================================================
# VOLATILITY NORMALIZATION SETTINGS
# ================================================================
RELIEF_EMA20_STRETCH_ATR = 2.5
EXTREME_EMA200_DISTANCE_ATR = 5.0

# ================================================================
# VETTED ASSET UNIVERSES — SPOT ONLY
# ================================================================
CORE_WATCHLIST = [
    "SOLUSDT", "XRPUSDT", "CNPYUSDT", "ADAUSDT", "SUIUSDT", "LINKUSDT",
    "XLMUSDT", "ALGOUSDT", "NIGHTUSDT", "POLUSDT", "FETUSDT", "TONUSDT",
    "AVAXUSDT", "NEARUSDT", "TRXUSDT", "KITEUSDT"
]

L1_L2_UNIVERSE = [
    "APTUSDT", "SEIUSDT", "INJUSDT", "TIAUSDT", "ARBUSDT",
    "OPUSDT", "HBARUSDT", "ICPUSDT", "FTMUSDT",
    "EGLDUSDT", "FLOWUSDT", "STXUSDT", "ROSEUSDT", "CELOUSDT"
]

AI_UNIVERSE = [
    "TAOUSDT", "RENDERUSDT", "GRTUSDT", "THETAUSDT", "AKTUSDT",
    "ARKMUSDT", "GLMUSDT", "RLCUSDT", "IOUSDT", "JASMYUSDT",
    "IQUSDT", "NMRUSDT", "PHBUSDT", "TRACUSDT"
]
