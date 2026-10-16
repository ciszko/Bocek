import asyncio

from bs4 import BeautifulSoup
from discord import Interaction, app_commands
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log
from utils.session import Session


def parse_slang(html: str) -> str:
    article = BeautifulSoup(html, "html.parser").find("article")
    word = article.find("h1").text
    desc = article.find("p").text.replace("\r\n", "").strip()
    return f"{word} - {desc}"


class Slang(RhymeExtension, Cog, name="slang"):
    def __init__(self, bot):
        self.bot = bot
        headers = {"User-Agent": "Bocek/1.0"}
        url = "https://www.miejski.pl"
        self.session = Session(url, headers)

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    @app_commands.command(name="slang", description="Losowy miejski.pl")
    async def slang(self, interaction: Interaction):
        await interaction.response.defer()
        r = await self.session.get("/losuj")
        msg = parse_slang(await r.text())
        log.info(msg)
        if interaction.user.voice:
            await interaction.followup.send(msg)
            await self.bot.speech.say(msg)
        else:
            await interaction.followup.send(msg)


async def setup(bot) -> None:
    await bot.add_cog(Slang(bot))
