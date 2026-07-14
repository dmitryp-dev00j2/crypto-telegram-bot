import httpx
import logging
from typing import List
from cryptobot.feeds import MarketSnapshot

log = logging.getLogger(__name__)

BYBIT_BASE = "https://api.bybit.com"


class BybitFeed:
    def __init__(self, timeout: float = 10.0):
        self._client: httpx.AsyncClient | None = None
        self.timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BYBIT_BASE,
                timeout=self.timeout,
                headers={"User-Agent": "cryptobot/0.4"},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def fetch_snapshots(self) -> List[MarketSnapshot]:
        client = await self._get_client()
        try:
            r = await client.get("/v5/market/tickers", params={"category": "linear"})
            r.raise_for_status()
            body = r.json()
        except httpx.HTTPError as e:
            log.error(f"bybit request error: {e}")
            return []

        if body.get("retCode") != 0:
            log.warning(f"bybit api error code {body.get('retCode')}: {body.get('retMsg')}")
            return []

        items = body.get("result", {}).get("list", [])
        out = []
        for it in items:
            sym = it.get("symbol", "")
            if not sym.endswith("USDT"):
                continue

            try:
                # bybit sometimes gives empty string for new listings
                fr_raw = it.get("fundingRate")
                funding = float(fr_raw) if fr_raw else 0.0
                
                pred_raw = it.get("predictedDeliveryPrice") # not predicted funding, bybit uses ticker v5
                pred_rate = float(it["predictedFundingRate"]) if it.get("predictedFundingRate") else None

                mark = float(it.get("markPrice") or 0.0)
                index_p = float(it.get("indexPrice") or mark)
                last = float(it.get("lastPrice") or mark)
                
                # Bybit returns 0.052 for 5.2% in price24hPcnt
                change24h = float(it.get("price24hPcnt") or 0.0) * 100.0
                
                next_time = int(it.get("nextFundingTime")) if it.get("nextFundingTime") else None
                vol = float(it.get("turnover24h") or 0.0)

                out.append(
                    MarketSnapshot(
                        exchange="bybit",
                        symbol=sym,
                        mark_price=mark,
                        last_price=last,
                        price_change_percent_24h=change24h,
                        funding_rate=funding,
                        index_price=index_p,
                        predicted_funding_rate=pred_rate,
                        next_funding_time=next_time,
                        volume_24h_quote=vol,
                    )
                )
            except (ValueError, TypeError) as err:
                # FIXME: 10000LADYS or weird decimal precision bugs occasionally land here
                continue

        return out
