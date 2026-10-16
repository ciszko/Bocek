from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.config import CONFIG
from utils.glossary import Glossary
from utils.live_client import LiveClient
from utils.log import log
from utils.narrator import Narrator

if TYPE_CHECKING:
    from bot import MyBot

OFFLINE_WAIT = CONFIG["rito"]["offline-wait"]
ONLINE_WAIT = CONFIG["rito"]["online-wait"]
EVENT_PRIORITY = CONFIG["rito"]["event-possibility"]
PLAYERS = CONFIG["rito"]["players"]
LOL_GAME_IP = CONFIG["rito"]["lol-game-ip"]
LOL_GAME_PORT = CONFIG["rito"]["lol-game-port"]


class Rito(RhymeExtension, Cog, name="rito"):
    def __init__(self, bot):
        self.bot: MyBot = bot
        self.glossary = Glossary(self, "rito.json")
        self.source = LiveClient(bot.web, f"https://{LOL_GAME_IP}:{LOL_GAME_PORT}")
        self.narrator = Narrator(self.glossary, PLAYERS, EVENT_PRIORITY)
        self.rito_check.start()

    def cog_unload(self):
        self.rito_check.cancel()

    @tasks.loop(seconds=30)
    async def rito_check(self):
        if not await self.source.in_game():
            self.narrator.reset()
            if self.rito_check.seconds != OFFLINE_WAIT:
                self.rito_check.change_interval(seconds=OFFLINE_WAIT)
            return
        if self.rito_check.seconds != ONLINE_WAIT:
            self.rito_check.change_interval(seconds=ONLINE_WAIT)
        if not (snapshot := await self.source.events()):
            return
        try:
            msg = self.narrator.narrate(snapshot)
        except Exception as e:
            log.exception(e)
            return
        if msg:
            await self.bot.speech.say(msg, voice="random")

    @rito_check.before_loop
    async def rito_check_before_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot) -> None:
    await bot.add_cog(Rito(bot))
