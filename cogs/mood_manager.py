from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog

from utils.log import log

if TYPE_CHECKING:
    from bot import MyBot


class MoodManager(Cog, name="mood_manager"):
    def __init__(self, bot: MyBot) -> None:
        self.bot = bot
        self.mood_decay.start()

    def cog_unload(self) -> None:
        self.mood_decay.cancel()

    @tasks.loop(minutes=5)
    async def mood_decay(self) -> None:
        in_voice = bool(self.bot.vc and self.bot.vc.is_connected())
        self.bot.mood.decay(in_voice=in_voice)
        log.info(
            f"Mood decay tick: score={self.bot.mood._score}, mood={self.bot.mood.mood}"
        )

    @mood_decay.before_loop
    async def before_decay(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: MyBot) -> None:
    await bot.add_cog(MoodManager(bot))
