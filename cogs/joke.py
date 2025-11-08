import asyncio

from bs4 import BeautifulSoup
from discord import Interaction, app_commands
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.session import Session


class Joke(RhymeExtension, Cog, name="joke"):
    def __init__(self, bot):
        self.bot = bot
        headers = {"User-Agent": "Bocek/1.0"}
        url = "https://perelki.net"
        self.session = Session(url, headers)

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    @app_commands.command(name="żart", description="Losowy żarcik")
    async def random_joke(self, interaction: Interaction):
        r = await self.session.get("/random")
        dom = BeautifulSoup(await r.text(), "html.parser")
        joke = (
            dom.find("div", {"class": "content"})
            .find("div", {"class": "container"})
            .get_text()
        )
        msg = (
            joke[: joke.find("Dowcip:")]
            .replace("\r", "")
            .replace("\n", " ")
            .replace("\t", "")
        )
        await interaction.response.send_message(msg)
        if interaction.user.voice:
            tts = await self.bot.tts.create_tts(msg)
            await self.bot.play_on_channel(tts)


async def setup(bot) -> None:
    await bot.add_cog(Joke(bot))
