from bs4 import BeautifulSoup
from discord import Interaction, app_commands
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log
from utils.replies import defer, reply, reply_and_speak
from utils.web import FetchError

JOKE_URL = "https://perelki.net/losuj"
# perelki.net redirects non-browser User-Agents to itself forever
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
}


def parse_joke(html: str) -> str:
    dom = BeautifulSoup(html, "html.parser")
    joke = dom.find("section", {"class": "losuj"}).find("p", {"class": "setup"})
    return " ".join(joke.get_text().split())


class Joke(RhymeExtension, Cog, name="joke"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="żart", description="Losowy żarcik")
    async def random_joke(self, interaction: Interaction):
        if not await defer(interaction):
            return
        try:
            msg = parse_joke(await self.bot.web.text(JOKE_URL, headers=BROWSER_HEADERS))
        except (FetchError, AttributeError) as e:
            log.warning(f"Joke unavailable: {e!r}")
            await reply(interaction, "Kurde, nie mogę teraz znaleźć żartu :(")
            return
        await reply_and_speak(
            interaction,
            self.bot.speech,
            msg,
            speak=bool(interaction.user.voice) and msg,
        )


async def setup(bot) -> None:
    await bot.add_cog(Joke(bot))
