import pytest

from utils.live_client import LiveClient
from utils.log import log
from utils.web import FetchError, FetchTimeout, FetchUnreachable


class FakeWeb:
    def __init__(self, status=200, error=None, data=None):
        self.status_code = status
        self.error = error
        self.data = data
        self.calls = []

    async def status(self, url, **options):
        self.calls.append((url, options))
        if self.error:
            raise self.error
        return self.status_code

    async def json(self, url, **options):
        self.calls.append((url, options))
        if self.error:
            raise self.error
        return self.data


def client(**kwargs):
    return LiveClient(FakeWeb(**kwargs), "https://127.0.0.1:2999")


@pytest.fixture
def logged_errors():
    messages = []
    sink = log.add(lambda m: messages.append(m), level="ERROR")
    yield messages
    log.remove(sink)


async def test_in_game_when_event_data_available():
    assert await client(status=200).in_game() is True


async def test_not_in_game_on_non_200():
    assert await client(status=404).in_game() is False


async def test_probe_is_quick_unverified_and_not_retried():
    web = FakeWeb()
    await LiveClient(web, "https://h:2999").in_game()
    url, options = web.calls[0]
    assert url == "https://h:2999/liveclientdata/eventdata"
    assert options == {"timeout": 3, "retries": 0, "ssl": False}


@pytest.mark.parametrize("error", [FetchTimeout("t"), FetchUnreachable("u")])
async def test_not_in_game_when_unreachable_without_error_log(error, logged_errors):
    assert await client(error=error).in_game() is False
    assert logged_errors == []


async def test_unexpected_error_is_logged(logged_errors):
    assert await client(error=ValueError("boom")).in_game() is False
    assert logged_errors


async def test_events_returns_payload():
    assert await client(data={"Events": []}).events() == {"Events": []}


async def test_events_returns_none_when_request_fails(logged_errors):
    assert await client(error=FetchError("boom")).events() is None
    assert logged_errors
