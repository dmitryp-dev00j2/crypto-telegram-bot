import asyncio
import httpx
import logging
from typing import Dict, List
from cryptobot.feeds import MarketSnapshot

log = logging.getLogger(__name__)

BASE_URL = "https://fapi.binance.com"


class BinanceFeed:
    def __init__(self, timeout: float = 10.0):
        self._client: httpx.AsyncClient | None = None
        self.timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=self.timeout,
                headers={"User-Agent": "cryptobot/0.4"},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_snapshots(self) -> List[MarketSnapshot]:
        client = await self._get_client()
        
        # Binance split funding & 24h ticker info across two endpoints
        try:
            r_prem = await client.get("/fapi/v1/premiumIndex")
            if r_prem.status_code == 429:
                wait_s = int(r_prem.headers.get("Retry-After", 60))
                log.warning(f"binance 429 rate limit hit, backing off {wait_s}s")
                await asyncio.sleep(wait_s)
                return []
            r_prem.raise_for_status()
            prem_data = r_prem.json()
        except httpx.HTTPError as err:
            log.error(f"binance premiumIndex fetch failed: {err}")
            return []

        try:
            r_ticker = await client.get("/fapi/v1/ticker/24hr")
            r_ticker.raise_for_status()
            ticker_data = {item["symbol"]: item for item in r_ticker.json()}
        except httpx.HTTPError as err:
            log.error(f"binance 24hr ticker fetch failed: {err}")
            ticker_data = {}

        results = []
        for item in prem_data:
            sym = item.get("symbol", "")
            if not sym.endswith("USDT"):
                continue

            t = ticker_data.get(sym, {})
            try:
                mark = float(item["markPrice"])
                last = float(t.get("lastPrice")) if "lastPrice" in t else mark
                index_p = float(item.get("indexPrice", mark))
                change_pct = float(t.get("priceChangePercent", 0.0))
                rate = float(item.get("lastFundingRate", 0.0))
                next_time = int(item.get("nextFundingTime", 0))
                vol = float(t.get("quoteVolume", 0.0))

                results.append(
                    MarketSnapshot(
                        exchange="binance",
                        symbol=sym,
                        mark_price=mark,
                        last_price=last,
                        price_change_percent_24h=change_pct,
                        funding_rate=rate,
                        index_price=index_p,
                        predicted_funding_rate=None, # binance doesn't send next estimated in this endpoint
                        next_funding_time=next_time,
                        volume_24h_quote=vol,
                    )
                )
            except (ValueError, KeyError, TypeError):
                continue

        return results
