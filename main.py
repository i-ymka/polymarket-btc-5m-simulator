"""Polymarket Bitcoin 5m simulator — entry point.

Watches the live "Bitcoin 5m" Up/Down market and, in simulation only, places a
hypothetical $1 UP trade whenever UP can be bought at <= $0.10. Resolves each
round against Polymarket's official outcome, keeps running win/loss totals,
logs everything, and stores results in a CSV.

No wallet, no API keys, no real orders. Run:  python3 main.py   (Ctrl+C to stop)

Resolution note: Polymarket marks a 5m market officially resolved a few minutes
AFTER its window closes. So entered rounds are queued as "pending" and resolved
opportunistically during later windows — the loop never blocks and never skips
a window waiting for a result.
"""

import logging
import time

import requests

import config
import reporter
from polymarket import find_active_btc_5m_market, get_resolution, get_up_best_ask
from simulator import RoundState, SessionStats

log = logging.getLogger("main")


def try_resolve_pending(session, pending, stats):
    """Non-blocking pass: resolve & record any pending rounds that are ready.

    `pending` is a list of (slug, entry_price); resolved rounds are removed.
    """
    still_pending = []
    for slug, entry_price, entry_profit in pending:
        outcome = get_resolution(session, slug)
        if outcome is None:
            still_pending.append((slug, entry_price, entry_profit))
            continue
        won = (outcome.strip().lower() == "up")
        stats.record(won)
        log.info("RESULT round %s: outcome=%s -> %s | session W/L = %d/%d",
                 slug, outcome, "WIN" if won else "LOSS", stats.wins, stats.losses)
        reporter.append_result(
            round_slug=slug, entry_price=entry_price, potential_profit=entry_profit,
            outcome=outcome, won=won, wins_total=stats.wins,
            losses_total=stats.losses,
        )
    pending[:] = still_pending


def monitor_window(session, market, round_state, pending, stats):
    """Poll UP best ask until the window closes; simulate one entry if cheap.

    Pending resolutions are checked on every tick so results land promptly
    without a dedicated blocking wait.
    """
    while time.time() < market.window_end:
        best_ask = get_up_best_ask(session, market.up_token_id)
        if best_ask is None:
            log.info("Price check: UP ask unavailable (round %s)", market.slug)
        else:
            log.info("Price check: UP ask=$%.3f (round %s)", best_ask, market.slug)
            if round_state.should_enter(best_ask):
                round_state.enter(best_ask)

        try_resolve_pending(session, pending, stats)

        remaining = market.window_end - time.time()
        if remaining <= 0:
            break
        time.sleep(min(config.POLL_INTERVAL, remaining))


def run():
    session = requests.Session()
    stats = SessionStats()
    pending = []           # entered rounds awaiting official resolution
    processed = set()      # windows we've already monitored

    log.info("Bitcoin 5m simulator started (sim-only, entry when potential "
             "profit on a $%.2f UP bet <= $%.2f).",
             config.BET_SIZE, config.PROFIT_THRESHOLD)

    while True:
        try_resolve_pending(session, pending, stats)

        market = find_active_btc_5m_market(session)
        if market is None or market.slug in processed:
            time.sleep(config.POLL_INTERVAL)
            continue

        log.info("Tracking %s (ends %s UTC)", market.slug,
                 time.strftime("%H:%M:%S", time.gmtime(market.window_end)))
        round_state = RoundState(slug=market.slug)
        monitor_window(session, market, round_state, pending, stats)
        processed.add(market.slug)

        if round_state.entered:
            pending.append((market.slug, round_state.entry_price,
                            round_state.entry_profit))
            log.info("Round %s entered; awaiting official resolution.", market.slug)
        else:
            log.info("No entry in round %s (UP profit never <= $%.2f).",
                     market.slug, config.PROFIT_THRESHOLD)


def main():
    reporter.setup_logging()
    try:
        run()
    except KeyboardInterrupt:
        log.info("Stopped by user. Results saved to %s.", config.OUTPUT_PATH)


if __name__ == "__main__":
    main()
