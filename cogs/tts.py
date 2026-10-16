from __future__ import annotations

from typing import TYPE_CHECKING, List

from discord import File, Interaction, app_commands
from discord.ext.commands import Cog

if TYPE_CHECKING:
    from bot import MyBot


class Tts(Cog, name="tts"):
    def __init__(self, bot):
        self.bot: MyBot = bot

    async def voices_autocomplete(
        self, interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        voices = await self.bot.speech.voices()
        choices = [
            app_commands.Choice(name=voice_name, value=value)
            for voice_name, value in voices.items()
            if current.lower() in voice_name.lower()
        ]
        return choices[:25]

    @app_commands.command(name="tts", description="Wysyła plik z nagraniem.")
    @app_commands.describe(text="Tekst do powiedzenia")
    @app_commands.describe(pitch="Wysokość głosu")
    @app_commands.autocomplete(voice=voices_autocomplete)
    @app_commands.describe(volume="Głośność")
    @app_commands.describe(speaking_rate="Szybkość mówienia")
    async def tts(
        self,
        interaction: Interaction,
        text: str,
        pitch: app_commands.Range[float, -20.0, 20.0] = 0,
        voice: str = "pl-PL-Wavenet-B",
        volume: app_commands.Range[float, 0.0, 1.0] = 0,
        speaking_rate: app_commands.Range[float, 0.25, 4.0] = 0.9,
    ):
        await interaction.response.defer()
        voice = voice if isinstance(voice, str) else voice.value
        tts_path = await self.bot.speech.synthesize(
            text,
            pitch=pitch,
            voice=voice,
            volume=volume,
            speaking_rate=speaking_rate,
        )
        if tts_path is None:
            await interaction.followup.send(
                "Mam sucho w gardle, nie mogę tego powiedzieć"
            )
            return
        await interaction.followup.send(file=File(tts_path))


async def setup(bot) -> None:
    await bot.add_cog(Tts(bot))
