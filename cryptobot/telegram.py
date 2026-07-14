import asyncio
import httpx
import logging

log = logging.getLogger(__name__)


class TelegramNotifier:
    """Minimal async sender for Telegram Bot API messages."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=12.0)

    async def stop(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def send_message(self, text: str, retries: int = 3) -> bool:
        if self._client is None:
            await self.start()

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        for attempt in range(retries):
            try:
                assert self._client is not None
                r = await self._client.post(url, json=payload)

                if r.status_code == 429:
                    retry_after = 2.0
                    try:
                        body = r.json()
                        retry_after = float(body.get("parameters", {}).get("retry_after", 2.0))
                    except Exception:
                        pass
                    log.warning("hit telegram 429, sleeping %.1fs", retry_after)
                    await asyncio.sleep(retry_after + 0.2)
                    continue

                if r.status_code == 400 and "can't parse entities" in r.text:
                    # telegram couldn't parse markdown, fallback to plain text
                    log.warning("tg markdown parse error, sending plain text")
                    fallback_payload = dict(payload)
                    del fallback_payload["parse_mode"]
                    r = await self._client.post(url, json=fallback_payload)

                r.raise_for_status()
                return True
            except httpx.HTTPError as err:
                log.error("telegram request error (attempt %d/%d): %s", attempt + 1, retries, err)
                if attempt < retries - 1:
                    await asyncio.sleep(1.5 * (attempt + 1))
            except Exception as e:
                log.error("unexpected tg error: %s", e)
                break
        return False
