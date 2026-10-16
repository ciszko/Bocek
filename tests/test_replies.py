import asyncio

import discord
import pytest

from utils.replies import defer, reply, reply_and_speak


class Resp:
    def __init__(self, error=None, delay=0.0):
        self.error = error
        self.delay = delay
        self.deferred = None

    async def defer(self, **kwargs):
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        self.deferred = kwargs


class Followup:
    def __init__(self, error=None):
        self.error = error
        self.sent = []
        self.times = []

    async def send(self, *args, **kwargs):
        if self.error:
            raise self.error
        self.sent.append((args, kwargs))
        self.times.append(asyncio.get_running_loop().time())


class FakeInteraction:
    def __init__(self, defer_error=None, send_error=None, defer_delay=0.0):
        self.response = Resp(defer_error, defer_delay)
        self.followup = Followup(send_error)


class FakeSpeech:
    def __init__(self, error=None, delay=0.0):
        self.error = error
        self.delay = delay
        self.said = []
        self.finished = False

    async def say(self, text, voice="default"):
        self.said.append((text, voice))
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        self.finished = True
        return True


def expired():
    resp = type("R", (), {"status": 404, "reason": "Not Found"})()
    return discord.errors.NotFound(resp, "Unknown interaction")


async def test_defer_fast():
    i = FakeInteraction()
    assert await defer(i) is True
    assert i.response.deferred == {"ephemeral": False}


async def test_defer_ephemeral_passthrough():
    i = FakeInteraction()
    await defer(i, ephemeral=True)
    assert i.response.deferred == {"ephemeral": True}


async def test_defer_slow_still_succeeds():
    assert await defer(FakeInteraction(defer_delay=0.05)) is True


async def test_defer_expired_returns_false():
    assert await defer(FakeInteraction(defer_error=expired())) is False


async def test_reply_sends_followup():
    i = FakeInteraction()
    assert await reply(i, "hi", ephemeral=True) is True
    assert i.followup.sent == [(("hi",), {"ephemeral": True})]


async def test_reply_on_expired_interaction_returns_false():
    assert await reply(FakeInteraction(send_error=expired()), "hi") is False


async def test_reply_and_speak_sends_text_without_waiting_for_speech():
    i = FakeInteraction()
    speech = FakeSpeech(delay=0.2)
    task = asyncio.create_task(reply_and_speak(i, speech, "tekst", speak="mowa"))
    await asyncio.sleep(0.05)
    assert i.followup.sent and not speech.finished
    await task
    assert speech.said == [("mowa", "random")]


async def test_speech_failure_never_blocks_text():
    i = FakeInteraction()
    await reply_and_speak(i, FakeSpeech(error=RuntimeError("boom")), "tekst")
    assert i.followup.sent == [(("tekst",), {})]


async def test_text_failure_does_not_stop_speech():
    speech = FakeSpeech()
    await reply_and_speak(FakeInteraction(send_error=expired()), speech, "tekst")
    assert speech.said == [("tekst", "random")]


async def test_no_speech_when_speak_is_false():
    i = FakeInteraction()
    speech = FakeSpeech()
    await reply_and_speak(i, speech, "tekst", speak=False)
    assert speech.said == [] and i.followup.sent


@pytest.mark.parametrize("voice", ["default", "random"])
async def test_voice_passthrough(voice):
    speech = FakeSpeech()
    await reply_and_speak(FakeInteraction(), speech, "t", voice=voice)
    assert speech.said == [("t", voice)]
