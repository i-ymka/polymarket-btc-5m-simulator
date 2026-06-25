"""Read-only Polymarket client for the Bitcoin 5m simulator.

Only public endpoints are used (Gamma for discovery, CLOB for order book).
No wallet, no API keys, no signing — the bot never trades for real.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests

import config

log = logging.getLogger(__name__)


@dataclass
class Market:
    """The data the simulator needs about one 5-minute Up/Down round."""
    market_id: str
    slug: str
    question: str
    up_token_id: str        # CLOB token id for the "Up" outcome
    down_token_id: str      # kept for completeness / resolution reads
    window_start: float     # unix seconds, aligned to 5-min boundary
    window_end: float       # unix seconds = window_start + WINDOW_SECONDS


def _current_window_start(now: Optional[float] = None) -> int:
    """Unix start of the 5-minute window that contains `now` (300s aligned)."""
    if now is None:
        now = time.time()
    return int(now // config.WINDOW_SECONDS * config.WINDOW_SECONDS)


def _parse_json_field(value):
    """Gamma returns `outcomes`/`clobTokenIds` as JSON-encoded strings."""
    if isinstance(value, str):
        return json.loads(value)
    return value


def _get_market_by_slug(session: requests.Session, slug: str) -> Optional[dict]:
    """Fetch the single market for an event slug via Gamma, or None on any
    failure / empty response (never raises)."""
    try:
        resp = session.get(
            f"{config.GAMMA_BASE}/events",
            params={"slug": slug},
            timeout=config.HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        events = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("Gamma request failed for %s: %s", slug, exc)
        return None

    if not events:
        return None
    markets = events[0].get("markets") or []
    return markets[0] if markets else None


def find_active_btc_5m_market(session: requests.Session,
                              now: Optional[float] = None) -> Optional[Market]:
    """Return the currently-open 5-minute BTC Up/Down market, or None.

    Discovery is deterministic: the 5m market slug is
    ``btc-updown-5m-<window_start>`` where window_start is aligned to 5-minute
    boundaries, so we compute the slug directly and look it up — no scanning.

    Returns None (without raising) when there is no open window, the market is
    already closed, or Gamma is unreachable / returns an empty/odd payload.
    """
    if now is None:
        now = time.time()
    start = _current_window_start(now)
    slug = f"{config.MARKET_5M_SLUG_PREFIX}{start}"

    market = _get_market_by_slug(session, slug)
    if market is None:
        log.info("No active 5m market for window %s (slug=%s)", start, slug)
        return None
    if market.get("closed"):
        log.info("Market %s is already closed", slug)
        return None

    try:
        outcomes = _parse_json_field(market.get("outcomes"))
        token_ids = _parse_json_field(market.get("clobTokenIds"))
    except (ValueError, TypeError) as exc:
        log.warning("Could not parse outcomes/tokens for %s: %s", slug, exc)
        return None

    if not outcomes or not token_ids or len(outcomes) != len(token_ids):
        log.warning("Outcomes/tokens mismatch for %s: %s / %s",
                    slug, outcomes, token_ids)
        return None

    # Map UP by NAME, never by index position, per project decision.
    name_to_token = {str(name).strip().lower(): tok
                     for name, tok in zip(outcomes, token_ids)}
    up_token = name_to_token.get("up")
    down_token = name_to_token.get("down")
    if up_token is None:
        log.warning("No 'Up' outcome found for %s: outcomes=%s", slug, outcomes)
        return None

    return Market(
        market_id=str(market.get("id")),
        slug=slug,
        question=market.get("question") or "",
        up_token_id=str(up_token),
        down_token_id=str(down_token) if down_token is not None else "",
        window_start=float(start),
        window_end=float(start + config.WINDOW_SECONDS),
    )


def get_up_best_ask(session: requests.Session, token_id: str) -> Optional[float]:
    """Best (lowest) ask for the UP token = the cheapest price to buy it now.

    Computed directly from the order book as min(ask price) so it is robust to
    book ordering. Returns None if the book is empty or the read fails.
    """
    try:
        resp = session.get(
            f"{config.CLOB_BASE}/book",
            params={"token_id": token_id},
            timeout=config.HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        book = resp.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("Order book read failed for token %s: %s", token_id, exc)
        return None

    asks = book.get("asks") or []
    prices = []
    for level in asks:
        try:
            prices.append(float(level["price"]))
        except (KeyError, TypeError, ValueError):
            continue
    if not prices:
        log.debug("No asks in book for token %s", token_id)
        return None
    return min(prices)


def get_resolution(session: requests.Session, slug: str) -> Optional[str]:
    """Read the official resolved outcome ("Up" or "Down") for a closed market.

    A resolved 5m market has closed=True and outcomePrices like ["1","0"]
    (index-aligned with outcomes). Returns the winning outcome name, or None if
    the market is not resolved yet / the read fails.
    """
    market = _get_market_by_slug(session, slug)
    if market is None or not market.get("closed"):
        return None
    try:
        outcomes = _parse_json_field(market.get("outcomes"))
        prices = _parse_json_field(market.get("outcomePrices"))
    except (ValueError, TypeError):
        return None
    if not outcomes or not prices or len(outcomes) != len(prices):
        return None

    for name, price in zip(outcomes, prices):
        try:
            if float(price) == 1.0:
                return str(name)
        except (TypeError, ValueError):
            continue
    return None
