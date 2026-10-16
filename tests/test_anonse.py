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
