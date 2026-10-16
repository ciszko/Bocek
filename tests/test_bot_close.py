from types import SimpleNamespace

import discord
import pytest
from discord.ext.commands import Bot

from bot import MyBot


@pytest.fixture
def bot(monkeypatch):
    monkeypatch.setenv("VOICE_CHANNEL_ID", "1")
    monkeypatch.setenv("TEXT_CHANNEL_ID", "2")
    return MyBot(command_prefix="$", intents=discord.Intents.none())


async def test_close_disconnects_voice_then_closes_bot(bot, monkeypatch):
    calls = []

    async def shutdown():
        calls.append("speech")

    async def parent_close(self):
        calls.append("parent")

    bot.speech = SimpleNamespace(shutdown=shutdown)
    monkeypatch.setattr(Bot, "close", parent_close)
    await bot.close()
    assert calls == ["speech", "parent"]


async def test_close_works_before_speech_is_created(bot, monkeypatch):
    calls = []

    async def parent_close(self):
        calls.append("parent")

    monkeypatch.setattr(Bot, "close", parent_close)
    await bot.close()
    assert calls == ["parent"]
