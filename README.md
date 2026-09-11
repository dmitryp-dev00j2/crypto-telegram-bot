# cryptobot

Small background daemon I run on a VPS to track perp funding rate spikes and sudden price moves on Binance and Bybit. It posts markdown alerts directly to a private Telegram channel via raw Bot API calls (no heavy bot frameworks).

## Setup

```bash
git clone https://github.com/username/cryptobot.git
cd cryptobot
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Config

Set these in `.env` or your shell environment:

```bash
TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
TELEGRAM_CHAT_ID="-100123456789"

# Alert thresholds
FUNDING_RATE_THRESHOLD="0.0005"   # 0.05% per 8h window
PRICE_MOVE_THRESHOLD="0.03"       # 3% move between checks
CHECK_INTERVAL_SEC="60"

# Optional filters
EXCLUDED_SYMBOLS="USDCUSDT,BUSDUSDT,FDUSDUSDT"
BYBIT_CATEGORY="linear"           # linear or inverse
STATE_DB_PATH="alerts.db"
```

## Running

Directly:
```bash
cryptobot
```

Or run as a systemd unit on your server.

## Tests

```bash
pytest
```

<!-- updated: 2026-09-11 -->
