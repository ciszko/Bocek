import asyncio

import aiohttp

from utils.log import log


class FetchError(Exception):
    pass


class FetchTimeout(FetchError):
    pass


class FetchUnreachable(FetchError):
    pass


class Web:
    """Shared HTTP fetching: one session, a hard deadline, bounded retries."""

    def __init__(
        self,
        user_agent: str = "Bocek/1.0",
        timeout: float = 8.0,
        retries: int = 1,
        backoff: float = 0.3,
    ):
        self._headers = {"User-Agent": user_agent}
        self._timeout = timeout
        self._retries = retries
        self._backoff = backoff
        self._session: aiohttp.ClientSession | None = None

    def _client(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def text(self, url: str, **options) -> str:
        return (await self._get(url, "text", **options))[1]

    async def json(self, url: str, **options):
        return (await self._get(url, "json", **options))[1]

    async def read(self, url: str, **options) -> bytes:
        return (await self._get(url, "read", **options))[1]

    async def status(self, url: str, **options) -> int:
        """Status code of a GET; HTTP error codes are returned, not raised."""
        return (await self._get(url, None, raise_for_status=False, **options))[0]

    async def close(self):
        if self._session is not None:
            await self._session.close()

    async def _get(
        self,
        url: str,
        body: str | None,
        headers: dict | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        ssl: bool = True,
        raise_for_status: bool = True,
    ):
        timeout = self._timeout if timeout is None else timeout
        attempts = 1 + (self._retries if retries is None else retries)
        last: FetchError | None = None
        for attempt in range(attempts):
            if attempt:
                await asyncio.sleep(self._backoff * attempt)
            try:
                async with asyncio.timeout(timeout):
                    async with self._client().get(
                        url, headers=headers, ssl=ssl
                    ) as resp:
                        if raise_for_status and resp.status >= 400:
                            last = FetchError(f"{url} returned {resp.status}")
                            if resp.status < 500:
                                raise last
                            continue
                        data = await getattr(resp, body)() if body else None
                        return resp.status, data
            except TimeoutError:
                last = FetchTimeout(f"{url} timed out after {timeout}s")
            except aiohttp.TooManyRedirects as e:
                raise FetchError(f"{url} redirects forever") from e
            except aiohttp.ClientConnectionError as e:
                last = FetchUnreachable(f"{url} unreachable: {e}")
            except aiohttp.ClientError as e:
                raise FetchError(f"{url} failed: {e}") from e
            log.debug(f"Fetch attempt {attempt + 1}/{attempts} failed: {last}")
        assert last is not None
        raise last
