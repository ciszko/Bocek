import requests
from requests.adapters import HTTPAdapter, Retry


class Session(requests.Session):
    def __init__(self, base_url, headers):
        self.base_url = base_url
        super().__init__()
        self.headers.update(**headers)

        retries = Retry(total=5,
                        backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])

        self.mount('http://', HTTPAdapter(max_retries=retries))
        self.mount('https://', HTTPAdapter(max_retries=retries))

    def get(self, url, **kwargs):
        _url = f'{self.base_url}{url}'
        return super().get(_url, **kwargs)
