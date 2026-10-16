from utils.log import log
from utils.web import FetchTimeout, FetchUnreachable


class LiveClient:
    """Adapter for the LoL Game Client API behind the Rito event-source seam."""

    def __init__(self, web, base_url: str):
        self._web = web
        self._url = f"{base_url}/liveclientdata/eventdata"

    async def in_game(self) -> bool:
        try:
            status = await self._web.status(self._url, timeout=3, retries=0, ssl=False)
            return status == 200
        except (FetchTimeout, FetchUnreachable):
            return False
        except Exception as e:
            log.exception(f"Unexpected error in in_game: {e}")
            return False

    async def events(self) -> dict | None:
        try:
            return await self._web.json(self._url, retries=0, ssl=False)
        except Exception as e:
            log.exception(e)
            return None
