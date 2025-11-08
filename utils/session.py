from aiohttp import ClientSession
from aiohttp_retry import ExponentialRetry, RetryClient
from yarl import URL


class Session:
    def __init__(self, base_url, headers=None, retries: bool = True):
        self._base_url = URL(base_url)
        self._session = RetryClient(
            client_session=ClientSession(headers=headers),
            retry_options=ExponentialRetry(attempts=3) if retries else None,
        )

    async def get(self, url, **kwargs):
        return await self._session.get(self._base_url / url, **kwargs)

    async def close(self):
        await self._session.close()