from niquests import AsyncSession
from urllib3.util import Retry

retries = Retry(total=3, backoff_factor=0.1)


class Session(AsyncSession):
    def __init__(self, base_url, headers=None):
        self.base_url = base_url
        self.headers = headers
        super().__init__(retries=retries, base_url=base_url)
