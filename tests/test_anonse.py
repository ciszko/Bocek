import asyncio

from cogs.anonse import first_usable, list_url


def test_list_url_without_region():
    url = list_url(2, "7", "0")
    assert url == "https://anonse.inaczej.pl/?m=list&pg=2&cat=7"


def test_list_url_with_region_is_not_duplicated():
    url = list_url(2, "7", "12")
    assert url == "https://anonse.inaczej.pl/?m=list&pg=2&cat=7&region=12"


async def test_first_usable_wins_and_others_are_cancelled():
    cancelled = []

    async def fetch(page):
        try:
            await asyncio.sleep({1: 5, 2: 0.01, 3: 5}[page])
        except asyncio.CancelledError:
            cancelled.append(page)
            raise
        return page if page == 2 else None

    assert await first_usable(fetch, [1, 2, 3]) == 2
    await asyncio.sleep(0)
    assert sorted(cancelled) == [1, 3]


async def test_concurrency_cap_is_respected():
    running = peak = 0

    async def fetch(page):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return None

    assert await first_usable(fetch, range(1, 8), concurrency=3) is None
    assert peak == 3


async def test_skips_unusable_pages_until_one_qualifies():
    async def fetch(page):
        return "ad" if page == 4 else None

    assert await first_usable(fetch, [1, 2, 3, 4, 5], concurrency=2) == "ad"


async def test_returns_none_when_nothing_found():
    async def fetch(page):
        return None

    assert await first_usable(fetch, [1, 2]) is None
    assert await first_usable(fetch, []) is None


class FakeInteraction:
    def __init__(self, name="kuba"):
        self.user = name
        self.edits = 0
        self.deferred = 0
        outer = self

        class Message:
            async def edit(self, **kwargs):
                outer.edits += 1
                await asyncio.sleep(0.01)

        class Response:
            async def defer(self):
                outer.deferred += 1

        self.message = Message()
        self.response = Response()


async def test_simultaneous_delete_clicks_add_one_view_button():
    from discord import Embed

    from cogs.anonse import Anonse

    view = Anonse.DeleteImageButton(msg="m", img="https://x/i.jpg", embed=Embed())
    clicks = [FakeInteraction("a"), FakeInteraction("b"), FakeInteraction("c")]
    await asyncio.gather(*(view.on_click.callback(i) for i in clicks))

    assert len(view.children) == 2
    assert sum(i.edits for i in clicks) == 1
    assert sum(i.deferred for i in clicks) == 3


async def test_delete_click_is_logged():
    from discord import Embed

    from cogs.anonse import Anonse
    from utils.log import log

    messages = []
    sink = log.add(lambda m: messages.append(str(m)), level="INFO")
    try:
        view = Anonse.DeleteImageButton(msg="m", img="https://x/i.jpg", embed=Embed())
        await view.on_click.callback(FakeInteraction("kuba"))
    finally:
        log.remove(sink)
    assert any("kuba" in m and "https://x/i.jpg" in m for m in messages)
