# Polymarket Bitcoin 5m Simulator Bot

A lightweight Python bot that watches Polymarket's **"Bitcoin 5m" (Up/Down)**
market in real time and, **in simulation only**, places a hypothetical **$1 UP**
trade whenever UP is a near-certain favorite — specifically when the **potential
profit on a $1 bet is ≤ $0.10** (UP priced at ~$0.909 or higher). It resolves
each round against Polymarket's official outcome, keeps running win/loss totals
for the session, logs every step, and stores results in a CSV.

> **No live orders. No wallet. No API keys.** The bot only reads public
> Polymarket endpoints. Everything stays strictly in simulation.

## How it works

1. **Find the active market** — the current 5-minute window's market is looked up
   deterministically from its slug (`btc-updown-5m-<unix>`, aligned to 5-minute
   boundaries) via the Gamma API. No scanning, never gets stuck on a stale
   contract.
2. **Monitor the window** — every `POLL_INTERVAL` seconds it reads the UP token's
   **best ask** from the CLOB order book and computes the potential profit on a
   $1 bet (`profit = (1 − price) / price`). The first time that profit is ≤ $0.10
   it simulates a **$1 UP buy** and locks the round (one trade per round).
3. **Resolve** — after the window closes it reads Polymarket's **official result**
   (Up/Down), records win/loss, updates session totals, and appends a CSV row.
4. **Repeat** for the next 5-minute window until you stop it (Ctrl+C).

Polymarket marks a 5m market officially resolved a few minutes *after* its
window closes, so entered rounds are queued and resolved opportunistically
during later windows — the bot never blocks or skips a window waiting.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Requires Python 3.10+.

## Run / stop

```bash
python3 main.py
```

Press **Ctrl+C** to stop. Results are saved to `results.csv` (configurable).

## Configuration

All options have sensible defaults and can be overridden with environment
variables — no code editing needed:

| Variable | Default | Meaning |
|---|---|---|
| `BOT_PROFIT_THRESHOLD` | `0.10` | Simulate a buy when potential profit on the $1 bet ≤ this (USD) |
| `BOT_BET_SIZE` | `1.0` | Hypothetical stake per trade (USD) |
| `BOT_POLL_INTERVAL` | `2.0` | Seconds between price checks inside a window |
| `BOT_OUTPUT_PATH` | `results.csv` | Where the results CSV is written |
| `BOT_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, ...) |
| `BOT_GAMMA_BASE` | `https://gamma-api.polymarket.com` | Gamma API base URL |
| `BOT_CLOB_BASE` | `https://clob.polymarket.com` | CLOB API base URL |
| `BOT_HTTP_TIMEOUT` | `15` | Seconds per HTTP request |

Example:

```bash
BOT_LOG_LEVEL=DEBUG BOT_OUTPUT_PATH=run1.csv python3 main.py
```

## Output

`results.csv` stores one row per simulated trade:

| Column | Description |
|---|---|
| `timestamp_utc` | When the result was recorded |
| `round_slug` | Which 5-minute market |
| `entry_price` | UP best ask at simulated entry |
| `potential_profit` | Profit on the $1 bet if UP wins (what drove the entry) |
| `bet_size` | Hypothetical stake (USD) |
| `outcome` | Official resolution (`Up`/`Down`) |
| `result` | `win` / `loss` for our UP bet |
| `wins_total` / `losses_total` | Running session totals |

A real sample run is included as `sample_results.csv`.

### Example console output

```
2026-06-24 01:00:29 INFO main: Bitcoin 5m simulator started (sim-only, entry when potential profit on a $1.00 UP bet <= $0.10).
2026-06-24 01:00:30 INFO main: Tracking btc-updown-5m-1782262500 (ends 01:05:00 UTC)
2026-06-24 01:00:30 INFO main: Price check: UP ask=$0.860 (round btc-updown-5m-1782262500)
2026-06-24 01:00:33 INFO main: Price check: UP ask=$0.910 (round btc-updown-5m-1782262500)
2026-06-24 01:00:33 INFO simulator: SIMULATED ENTRY: $1.00 on UP at price=$0.910 (potential profit $0.099) (round btc-updown-5m-1782262500)
2026-06-24 01:05:00 INFO main: Round btc-updown-5m-1782262500 entered; awaiting official resolution.
2026-06-24 01:09:12 INFO main: RESULT round btc-updown-5m-1782262500: outcome=Up -> WIN | session W/L = 1/0
```

## Files

| File | Role |
|---|---|
| `main.py` | Entry point + main loop |
| `polymarket.py` | Read-only Polymarket client (Gamma discovery, CLOB book, resolution) |
| `simulator.py` | Entry trigger, per-round lock, session win/loss totals |
| `reporter.py` | Logging setup + CSV persistence |
| `config.py` | Defaults + environment-variable overrides |
