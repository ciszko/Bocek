import os
from functools import cached_property

from discord import Interaction, app_commands
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log
from utils.session import Session


class Minecraft(RhymeExtension, Cog, name="minecraft"):
    def __init__(self, bot):
        self.bot = bot
        base_url = "https://api.exaroton.com/v1"
        token = os.getenv("MINECRAFT_SERVER_TOKEN")
        headers = {"User-Agent": "Bocek/1.0", "Authorization": f"Bearer {token}"}
        self.session = Session(base_url, headers)

    @cached_property
    async def server_id(self):
        resp = await self.session.get("/servers").json()
        return next(s["id"] for s in resp["data"] if s["name"] == "Xubek")

    @app_commands.command(
        name="minecraft_start", description="Startuje serwer minkraft"
    )
    async def minecraft_start(self, interaction: Interaction):
        resp = await self.session.get(f"/servers/{self.server_id}/start").json()
        if resp["success"] is False:
            await interaction.response.send_message(
                "Kurde, nie mogę włączyć serwerka :("
            )
            return
        log.info("Turning on minecraft server")
        await interaction.response.send_message("Serwer minkraft działa!")

    @app_commands.command(name="minecraft_stop", description="Stopuje serwer minkraft")
    async def minecraft_stop(self, interaction: Interaction):
        resp = await self.session.get(f"/servers/{self.server_id}/stop").json()
        if resp["success"] is False:
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
        resp = await self.session.get("/account").json()
        if resp["success"] is False:
            await interaction.response.send_message(
                "Kurde, nie mogę wyłączyć serwerka :("
            )
            return
        credits = resp["data"]["credits"]
        log.info(f"Remaining credits for server: {credits}")
        await interaction.response.send_message(f"Zostało **{credits}** kredytów.")


async def setup(bot) -> None:
    await bot.add_cog(Minecraft(bot))
