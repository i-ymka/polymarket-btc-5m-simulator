"""Simulation logic: entry trigger, per-round lock, and session win/loss totals.

Everything here is hypothetical — no real orders are ever placed.
"""

import logging
from dataclasses import dataclass, field

import config

log = logging.getLogger(__name__)


@dataclass
class SessionStats:
    """Running totals of simulated trades for the whole session."""
    wins: int = 0
    losses: int = 0

    @property
    def total(self) -> int:
        return self.wins + self.losses

    def record(self, won: bool) -> None:
        if won:
            self.wins += 1
        else:
            self.losses += 1


def profit_for(best_ask: float) -> float:
    """Potential profit on a $BET_SIZE UP bet bought at price `best_ask`.

    Buying for $BET_SIZE at price p gives BET_SIZE/p shares, each worth $1 if
    UP wins, so profit = BET_SIZE * (1 - p) / p.
    """
    return config.BET_SIZE * (1.0 - best_ask) / best_ask


@dataclass
class RoundState:
    """Tracks one 5-minute round: whether we've already simulated a trade."""
    slug: str
    entered: bool = False
    entry_price: float = 0.0
    entry_profit: float = 0.0

    def should_enter(self, best_ask: float) -> bool:
        """One simulated trade per round, only when UP is the favorite.

        Triggers when the potential profit on the bet is <= PROFIT_THRESHOLD
        (i.e. UP is priced high). Needs a valid ask in (0, 1].
        """
        if self.entered or best_ask is None or not (0.0 < best_ask <= 1.0):
            return False
        return profit_for(best_ask) <= config.PROFIT_THRESHOLD

    def enter(self, best_ask: float) -> None:
        self.entered = True
        self.entry_price = best_ask
        self.entry_profit = profit_for(best_ask)
        log.info(
            "SIMULATED ENTRY: $%.2f on UP at price=$%.3f (potential profit "
            "$%.3f) (round %s)",
            config.BET_SIZE, best_ask, self.entry_profit, self.slug,
        )
