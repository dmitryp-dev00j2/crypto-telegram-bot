import asyncio
import logging
import time
from typing import Dict, List, Tuple
from cryptobot.config import Config
from cryptobot.feeds import BinanceFeed, BybitFeed, MarketSnapshot
from cryptobot.telegram import TelegramNotifier
from cryptobot.storage import StateStore
from cryptobot.formatters import (
    format_funding_alert,
    format_price_alert,
    format_spread_alert,
)

log = logging.getLogger(__name__)


class MarketMonitor:
    """Main orchestration loop collecting exchange data and firing alerts."""

    def __init__(self, config: Config, notifier: TelegramNotifier, store: StateStore):
        self.cfg = config
        self.tg = notifier
        self.store = store
        self.binance = BinanceFeed(timeout=config.http_timeout_sec)
        self.bybit = BybitFeed(timeout=config.http_timeout_sec)
        self._running = False
        # Key: alert_key -> timestamp of last notification
        self._cooldowns: Dict[str, float] = {}

    async def start(self):
        self._running = True
        log.info(f"starting monitor loop (interval={self.cfg.poll_interval_sec}s)")
        
        while self._running:
            t0 = time.monotonic()
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.exception(f"tick failed: {e}")

            elapsed = time.monotonic() - t0
            sleep_for = max(1.0, self.cfg.poll_interval_sec - elapsed)
            await asyncio.sleep(sleep_for)

    async def stop(self):
        self._running = False
        await self.binance.close()
        await self.bybit.close()

    def _check_cooldown(self, key: str, duration_sec: int) -> bool:
        now = time.time()
        last = self._cooldowns.get(key, 0.0)
        if (now - last) < duration_sec:
            return False
        self._cooldowns[key] = now
        return True

    async def _tick(self):
        # Fetch both concurrently to keep timestamps close
        res_b, res_by = await asyncio.gather(
            self.binance.fetch_snapshots(),
            self.bybit.fetch_snapshots(),
            return_exceptions=True,
        )

        binance_map: Dict[str, MarketSnapshot] = {}
        bybit_map: Dict[str, MarketSnapshot] = {}

        if isinstance(res_b, list):
            binance_map = {s.symbol: s for s in res_b}
        else:
            log.warning(f"binance fetch returned error: {res_b}")

        if isinstance(res_by, list):
            bybit_map = {s.symbol: s for s in res_by}
        else:
            log.warning(f"bybit fetch returned error: {res_by}")

        # print(f"debug: b={len(binance_map)} by={len(bybit_map)}")

        # 1. Individual exchange checks (funding spikes, 24h pump/dump, 1h fast move)
        all_snaps = list(binance_map.values()) + list(bybit_map.values())
        for snap in all_snaps:
            if snap.volume_24h_quote < self.cfg.min_24h_volume_usd:
                continue
            await self._evaluate_single_snapshot(snap)

        # 2. Cross exchange funding arb spread
        if self.cfg.enable_spread_alerts:
            await self._evaluate_cross_spreads(binance_map, bybit_map)

    async def _evaluate_single_snapshot(self, s: MarketSnapshot):
        # A. Funding rate extreme
        if abs(s.funding_rate) >= self.cfg.funding_alert_threshold:
            cd = self.cfg.funding_cooldown_sec
            key = f"fr:{s.exchange}:{s.symbol}"
            if self._check_cooldown(key, cd):
                txt = format_funding_alert(s)
                await self.tg.send_message(txt)

        # B. 24h high price change
        if abs(s.price_change_percent_24h) >= self.cfg.price_change_threshold_24h:
            cd = self.cfg.price_alert_cooldown_sec
            key = f"px24:{s.exchange}:{s.symbol}"
            if self._check_cooldown(key, cd):
                txt = format_price_alert(s, timeframe="24h", delta_pct=s.price_change_percent_24h)
                await self.tg.send_message(txt)

        # C. Short term spike against persisted historical price
        prev_price = self.store.get_price_1h_ago(s.exchange, s.symbol)
        self.store.record_price(s.exchange, s.symbol, s.mark_price)
        if prev_price and prev_price > 0:
            delta_1h = ((s.mark_price - prev_price) / prev_price) * 100.0
            if abs(delta_1h) >= self.cfg.price_change_threshold_1h:
                key = f"px1h:{s.exchange}:{s.symbol}"
                if self._check_cooldown(key, self.cfg.price_alert_cooldown_sec):
                    txt = format_price_alert(s, timeframe="1h", delta_pct=delta_1h)
                    await self.tg.send_message(txt)

    async def _evaluate_cross_spreads(self, b_map: Dict[str, MarketSnapshot], by_map: Dict[str, MarketSnapshot]):
        # Compare common symbols between Binance & Bybit
        common_symbols = set(b_map.keys()) & set(by_map.keys())
        for sym in common_symbols:
            sb = b_map[sym]
            sby = by_map[sym]

            # Skip if volume is negligible on either side
            if sb.volume_24h_quote < self.cfg.min_24h_volume_usd or sby.volume_24h_quote < self.cfg.min_24h_volume_usd:
                continue

            spread = abs(sb.funding_rate - sby.funding_rate)
            if spread >= self.cfg.spread_alert_threshold:
                key = f"spread:{sym}"
                if self._check_cooldown(key, self.cfg.funding_cooldown_sec):
                    msg = format_spread_alert(sb, sby, spread)
                    await self.tg.send_message(msg)
