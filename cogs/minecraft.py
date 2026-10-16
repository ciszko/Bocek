import os

from async_property import async_cached_property
from discord import Interaction, app_commands
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log


class Minecraft(RhymeExtension, Cog, name="minecraft"):
    def __init__(self, bot):
        self.bot = bot
        token = os.getenv("MINECRAFT_SERVER_TOKEN")
        self.headers = {"Authorization": f"Bearer {token}"}

    async def _api(self, path: str) -> dict:
        return await self.bot.web.json(
            f"https://api.exaroton.com/v1{path}", headers=self.headers
        )

    @async_cached_property
    async def server_id(self):
        data = await self._api("/servers")
        return next(s["id"] for s in data["data"] if s["name"] == "Xubek")

    @app_commands.command(
        name="minecraft_start", description="Startuje serwer minkraft"
    )
    async def minecraft_start(self, interaction: Interaction):
        data = await self._api(f"/servers/{await self.server_id}/start")
        if data["success"] is False:
            await interaction.response.send_message(
                "Kurde, nie mogę włączyć serwerka :("
            )
            return
        log.info("Turning on minecraft server")
        await interaction.response.send_message("Serwer minkraft działa!")

    @app_commands.command(name="minecraft_stop", description="Stopuje serwer minkraft")
    async def minecraft_stop(self, interaction: Interaction):
        data = await self._api(f"/servers/{await self.server_id}/stop")
        if data["success"] is False:
            await interaction.response.send_message(
                "Kurde, nie mogę wyłączyć serwerka :("
            )
            return
        log.info("Turning off minecraft server")
        await interaction.response.send_message("Serwer minkraft zamknięty!")

    @app_commands.command(
        name="minecraft_kredyty", description="Zwraca ilość pozostałych kredytów"
    )
    async def minecraft_credit(self, interaction: Interaction):
        data = await self._api("/account")
        if data["success"] is False:
            await interaction.response.send_message(
                "Kurde, nie mogę wyłączyć serwerka :("
            )
            return
        credits = data["data"]["credits"]
        log.info(f"Remaining credits for server: {credits}")
        await interaction.response.send_message(f"Zostało **{credits}** kredytów.")


async def setup(bot) -> None:
    await bot.add_cog(Minecraft(bot))
