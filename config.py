"""Configuration for the Polymarket Bitcoin 5m simulator bot.

Defaults below can be overridden with environment variables (handy for the
client to reconfigure without editing code), e.g.:

    BOT_LOG_LEVEL=DEBUG BOT_OUTPUT_PATH=run1.csv python3 main.py

No secrets / API keys live here — the bot only reads public Polymarket
endpoints and never places real orders.
"""

import os

# --- Polymarket public endpoints (read-only, no auth) ---
GAMMA_BASE = os.getenv("BOT_GAMMA_BASE", "https://gamma-api.polymarket.com")
CLOB_BASE = os.getenv("BOT_CLOB_BASE", "https://clob.polymarket.com")

# --- Trading-simulation rules (confirmed with client) ---
# Buy UP when the POTENTIAL PROFIT on a $BET_SIZE bet would be <= this (USD),
# i.e. when UP is the near-certain favorite. For a stake S bought at price p
# (per share, $1 payout if it wins), profit = S * (1 - p) / p. With S = $1 and
# the $0.10 threshold this triggers when UP's price is >= ~$0.909.
PROFIT_THRESHOLD = float(os.getenv("BOT_PROFIT_THRESHOLD", "0.10"))
BET_SIZE = float(os.getenv("BOT_BET_SIZE", "1.0"))

# --- 5-minute Bitcoin Up/Down market ---
# 5m markets use the slug "btc-updown-5m-<unix>" where <unix> is the window
# start, aligned to 5-minute boundaries (unix % 300 == 0). Window length = 300s.
MARKET_5M_SLUG_PREFIX = "btc-updown-5m-"
WINDOW_SECONDS = 300

# --- Runtime ---
POLL_INTERVAL = float(os.getenv("BOT_POLL_INTERVAL", "2.0"))  # s between price checks
HTTP_TIMEOUT = float(os.getenv("BOT_HTTP_TIMEOUT", "15"))     # s per HTTP request

LOG_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO")
OUTPUT_PATH = os.getenv("BOT_OUTPUT_PATH", "results.csv")
