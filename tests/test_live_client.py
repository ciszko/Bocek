import asyncio
from types import SimpleNamespace

import aiohttp
import pytest
from yarl import URL

from utils.live_client import LiveClient
from utils.log import log


class FakeSession:
    def __init__(self, status=200, error=None):
        self.status = status
        self.error = error

    async def get(self, url, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(status=self.status, release=lambda: None)


def connection_refused():
    key = SimpleNamespace(
        ssl=False, host="h", port=1, is_ssl=False, url=URL("http://h:1")
    )
    return aiohttp.ClientConnectorError(key, OSError("refused"))


@pytest.fixture
def logged_errors():
    messages = []
    sink = log.add(lambda m: messages.append(m), level="ERROR")
    yield messages
    log.remove(sink)


async def test_in_game_when_event_data_available():
    assert await LiveClient(FakeSession(200)).in_game() is True


async def test_not_in_game_on_non_200():
    assert await LiveClient(FakeSession(404)).in_game() is False


async def test_not_in_game_on_timeout_without_error_log(logged_errors):
    result = await LiveClient(FakeSession(error=asyncio.TimeoutError())).in_game()
    assert result is False
    assert logged_errors == []


async def test_not_in_game_on_connection_refused_without_error_log(logged_errors):
    result = await LiveClient(FakeSession(error=connection_refused())).in_game()
    assert result is False
    assert logged_errors == []


async def test_unexpected_error_is_logged(logged_errors):
    result = await LiveClient(FakeSession(error=ValueError("boom"))).in_game()
    assert result is False
    assert logged_errors


async def test_events_returns_none_when_request_fails(logged_errors):
    assert await LiveClient(FakeSession(error=ValueError("boom"))).events() is None
    assert logged_errors
