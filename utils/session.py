from niquests import AsyncSession
from urllib3.util import Retry

retries = Retry(total=3, backoff_factor=0.1)


class Session(AsyncSession):
    def __init__(self, base_url, headers=None, retries: bool = True):
        self.base_url = base_url
        self.headers = headers
        kwargs = {"base_url": base_url}
        if retries:
            kwargs["retries"] = retries
        super().__init__(**kwargs)
