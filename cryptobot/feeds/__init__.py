from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class MarketSnapshot:
    """Normalized perp ticker and funding rate for a single symbol."""
    exchange: str
    symbol: str
    mark_price: float
    last_price: float
    price_change_percent_24h: float
    funding_rate: float
    index_price: float = 0.0
    predicted_funding_rate: Optional[float] = None
    next_funding_time: Optional[int] = None
    volume_24h_quote: float = 0.0


from cryptobot.feeds.binance import BinanceFeed
from cryptobot.feeds.bybit import BybitFeed

__all__ = ["MarketSnapshot", "BinanceFeed", "BybitFeed"]
