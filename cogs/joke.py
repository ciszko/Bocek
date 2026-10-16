from bs4 import BeautifulSoup
from discord import Interaction, app_commands
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log
from utils.web import FetchError


def parse_joke(html: str) -> str:
    dom = BeautifulSoup(html, "html.parser")
    joke = (
        dom.find("div", {"class": "content"})
        .find("div", {"class": "container"})
        .get_text()
    )
    return (
        joke[: joke.find("Dowcip:")]
        .replace("\r", "")
        .replace("\n", " ")
        .replace("\t", "")
    )


class Joke(RhymeExtension, Cog, name="joke"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="żart", description="Losowy żarcik")
    async def random_joke(self, interaction: Interaction):
        await interaction.response.defer()
        try:
            msg = parse_joke(await self.bot.web.text("https://perelki.net/random"))
        except (FetchError, AttributeError) as e:
            log.warning(f"Joke unavailable: {e!r}")
            await interaction.followup.send("Kurde, nie mogę teraz znaleźć żartu :(")
            return
        await interaction.followup.send(msg)
        if interaction.user.voice:
            await self.bot.speech.say(msg, voice="random")


async def setup(bot) -> None:
    await bot.add_cog(Joke(bot))
