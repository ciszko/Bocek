import asyncio

import pytest
from aiohttp import web as aioweb
from aiohttp.test_utils import TestServer

from utils.web import FetchError, FetchTimeout, FetchUnreachable, Web


@pytest.fixture
async def server():
    calls = {"flaky": 0, "down": 0}

    async def ok(request):
        return aioweb.json_response({"ua": request.headers.get("User-Agent")})

    async def loop(request):
        raise aioweb.HTTPFound("/loop")

    async def slow(request):
        await asyncio.sleep(5)
        return aioweb.Response(text="late")

    async def flaky(request):
        calls["flaky"] += 1
        if calls["flaky"] == 1:
            return aioweb.Response(status=500)
        return aioweb.Response(text="ok")

    async def down(request):
        calls["down"] += 1
        return aioweb.Response(status=503)

    async def missing(request):
        return aioweb.Response(status=404)

    app = aioweb.Application()
    app.router.add_get("/ok", ok)
    app.router.add_get("/loop", loop)
    app.router.add_get("/slow", slow)
    app.router.add_get("/flaky", flaky)
    app.router.add_get("/down", down)
    app.router.add_get("/missing", missing)
    srv = TestServer(app)
    await srv.start_server()
    srv.calls = calls
    yield srv
    await srv.close()


@pytest.fixture
async def web(server):
    w = Web(timeout=0.5, backoff=0.0)
    yield w
    await w.close()


def url(server, path):
    return str(server.make_url(path))


async def test_json_sends_default_user_agent(web, server):
    assert await web.json(url(server, "/ok")) == {"ua": "Bocek/1.0"}


async def test_headers_are_per_call(web, server):
    data = await web.json(url(server, "/ok"), headers={"User-Agent": "x"})
    assert data == {"ua": "x"}


async def test_redirect_loop_fails_fast(web, server):
    with pytest.raises(FetchError):
        await web.text(url(server, "/loop"))


async def test_slow_server_times_out(web, server):
    with pytest.raises(FetchTimeout):
        await web.text(url(server, "/slow"), retries=0)


async def test_retries_server_error_once(web, server):
    assert await web.text(url(server, "/flaky")) == "ok"
    assert server.calls["flaky"] == 2


async def test_gives_up_after_retries(web, server):
    with pytest.raises(FetchError):
        await web.text(url(server, "/down"), retries=2)
    assert server.calls["down"] == 3


async def test_client_error_is_not_retried(web, server):
    with pytest.raises(FetchError):
        await web.text(url(server, "/missing"))


async def test_status_returns_code_without_raising(web, server):
    assert await web.status(url(server, "/missing")) == 404
    assert await web.status(url(server, "/ok")) == 200


async def test_unreachable_host(web):
    with pytest.raises(FetchUnreachable):
        await web.text("http://127.0.0.1:1/", retries=0)


async def test_read_returns_bytes(web, server):
    assert await web.read(url(server, "/flaky")) == b"ok"
