import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'\"")
        os.environ.setdefault(k, v)


@dataclass
class Config:
    """Runtime configuration loaded from environment or .env file."""
    tg_bot_token: str
    tg_chat_id: str
    poll_interval_sec: int = 60
    funding_threshold_pct: float = 0.05
    price_move_threshold_pct: float = 3.5
    min_volume_24h_usdt: float = 5_000_000.0
    binance_enabled: bool = True
    bybit_enabled: bool = True
    cooldown_minutes: int = 120
    db_path: str = "alerts.db"


def _to_bool(val: str) -> bool:
    return val.lower() in ("1", "true", "yes", "on")


def load_config(env_path: str = ".env") -> Config:
    _load_dotenv(Path(env_path))

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    return Config(
        tg_bot_token=token,
        tg_chat_id=chat_id,
        poll_interval_sec=int(os.getenv("POLL_INTERVAL", "60")),
        funding_threshold_pct=float(os.getenv("FUNDING_THRESHOLD_PCT", "0.05")),
        price_move_threshold_pct=float(os.getenv("PRICE_MOVE_THRESHOLD_PCT", "3.5")),
        min_volume_24h_usdt=float(os.getenv("MIN_VOLUME_24H_USDT", "5000000")),
        binance_enabled=_to_bool(os.getenv("BINANCE_ENABLED", "true")),
        bybit_enabled=_to_bool(os.getenv("BYBIT_ENABLED", "true")),
        cooldown_minutes=int(os.getenv("ALERT_COOLDOWN_MIN", "120")),
        db_path=os.getenv("SQLITE_PATH", "alerts.db"),
    )
