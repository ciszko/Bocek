import asyncio

import aiohttp

from utils.log import log


class LiveClient:
    """Adapter for the LoL Game Client API behind the Rito event-source seam."""

    def __init__(self, session):
        self._session = session

    async def in_game(self) -> bool:
        try:
            resp = await self._session.get(
                "/liveclientdata/eventdata", timeout=3, ssl=False
            )
            resp.release()
            return resp.status == 200
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError):
            return False
        except Exception as e:
            log.exception(f"Unexpected error in in_game: {e}")
            return False

    async def events(self) -> dict | None:
        try:
            resp = await self._session.get("/liveclientdata/eventdata", ssl=False)
            return await resp.json()
        except Exception as e:
            log.exception(e)
            return None
