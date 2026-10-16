from bs4 import BeautifulSoup
from discord import Interaction, app_commands
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log
from utils.replies import defer, reply, reply_and_speak
from utils.web import FetchError


def parse_slang(html: str) -> str:
    article = BeautifulSoup(html, "html.parser").find("article")
    word = article.find("h1").text
    desc = article.find("p").text.replace("\r\n", "").strip()
    return f"{word} - {desc}"


class Slang(RhymeExtension, Cog, name="slang"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="slang", description="Losowy miejski.pl")
    async def slang(self, interaction: Interaction):
        if not await defer(interaction):
            return
        try:
            msg = parse_slang(await self.bot.web.text("https://www.miejski.pl/losuj"))
        except (FetchError, AttributeError) as e:
            log.warning(f"Slang unavailable: {e!r}")
            await reply(interaction, "Kurde, nie mogę teraz znaleźć słowa :(")
            return
        log.info(msg)
        await reply_and_speak(
            interaction,
            self.bot.speech,
            msg,
            speak=bool(interaction.user.voice) and msg,
            voice="default",
        )


async def setup(bot) -> None:
    await bot.add_cog(Slang(bot))
