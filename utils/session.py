from aiohttp import ClientSession
from aiohttp_retry import RetryClient, ExponentialRetry


class Session(RetryClient):
    def __init__(self, base_url, headers):
        self.base_url = base_url
        session = ClientSession()
        session.headers.update(**headers)
        super().__init__(session)

    async def get(self, url, **kwargs):
        async with super().get(
            f"{self.base_url}{url}",
            retry_options=ExponentialRetry(),
            **kwargs,
        ) as response:
            resp = await response.text()
        # await self.close()
        return resp
