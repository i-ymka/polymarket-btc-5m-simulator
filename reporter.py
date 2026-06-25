"""Logging setup and CSV persistence of simulated trade outcomes."""

import csv
import logging
import os
import time

import config

CSV_FIELDS = [
    "timestamp_utc",     # when the result was recorded
    "round_slug",        # which 5-minute market
    "entry_price",       # UP best ask at simulated entry
    "potential_profit",  # profit on the bet if UP wins (drove the entry)
    "bet_size",          # hypothetical stake (USD)
    "outcome",           # "Up" or "Down" (official resolution)
    "result",            # "win" or "loss" for our UP bet
    "wins_total",        # running session totals after this trade
    "losses_total",
]


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def append_result(round_slug: str, entry_price: float, potential_profit: float,
                  outcome: str, won: bool, wins_total: int,
                  losses_total: int) -> None:
    """Append one simulated trade outcome to the CSV (writes header once)."""
    new_file = not os.path.exists(config.OUTPUT_PATH)
    with open(config.OUTPUT_PATH, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "round_slug": round_slug,
            "entry_price": f"{entry_price:.3f}",
            "potential_profit": f"{potential_profit:.3f}",
            "bet_size": f"{config.BET_SIZE:.2f}",
            "outcome": outcome,
            "result": "win" if won else "loss",
            "wins_total": wins_total,
            "losses_total": losses_total,
        })
