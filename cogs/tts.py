import random
from pathlib import Path
from typing import List
from uuid import uuid4

from async_property import async_cached_property
from discord import File, Interaction, app_commands
from discord.ext.commands import Cog
from google.api_core.exceptions import InvalidArgument, ServiceUnavailable
from google.api_core.retry_async import AsyncRetry
from google.cloud import texttospeech

from utils.common import BASE_DIR, MP3_DIR, RhymeExtension, async_wrap
from utils.log import log


class Tts(RhymeExtension, Cog, name="tts"):
    def __init__(self, bot):
        self.bot = bot
        self.client = texttospeech.TextToSpeechAsyncClient()

    @async_cached_property
    async def voices(self):
        voices_resp = await self.client.list_voices(language_code="pl-PL")
        return {
            f"{v.name}-{v.ssml_gender.name}": v.name
            for v in voices_resp.voices
            if "F" not in v.name
        }

    async def voices_autocomplete(
        self, interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        voices = await self.voices
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
        tts_path = await self.create_tts(
            text=text,
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

    async def create_tts(self, text, random=False, **kwargs):
        if not text:
            return None
        if random:
            kwargs.update(await self.get_random_voice())
        log.info(f"TTS args text={text}, kwargs={kwargs}")
        return await self.tts_google(text, **kwargs)

    async def tts_google(
        self,
        text,
        pitch=0.0,
        voice="pl-PL-Wavenet-B",
        volume=0.0,
        speaking_rate=0.9,
        lang="pl-PL",
    ):
        if not text:
            return None
        if lang.lower() == "pl":
            lang = "pl-PL"
        tts_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(language_code=lang, name=voice)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=pitch,
            volume_gain_db=volume,
            speaking_rate=speaking_rate,
        )
        try:
            response = await self.client.synthesize_speech(
                input=tts_input,
                voice=voice_params,
                audio_config=audio_config,
            )
        except InvalidArgument:
            audio_config.speaking_rate = None
            audio_config.pitch = None
            response = await self.client.synthesize_speech(
                input=tts_input,
                voice=voice_params,
                audio_config=audio_config,
            )
        except ServiceUnavailable:
            del self.voices
            await self.voices
            return self.get_random_fart()
        except Exception as exc:
            log.exception(f"TTS synthesis failed: {exc}")
            return None
        if response is None:
            return None
        tts_path = MP3_DIR / f"{uuid4().hex[:10]}.mp3"
        with tts_path.open("wb") as out:
            out.write(response.audio_content)
        return tts_path

    def get_random_fart(self) -> str:
        return random.choice(list((BASE_DIR / "farts").iterdir())).absolute().as_posix()

    @async_wrap
    def delete_tts(self, path):
        path = Path(path)
        try:
            path.unlink()
            log.info(f"Removed {path}")
        except FileNotFoundError:
            log.warning(f"{path} was already deleted")

    @async_wrap
    def delete_all_tts(self):
        log.info("Deleting all tts")
        for file in MP3_DIR.iterdir():
            try:
                file.unlink()
            except PermissionError:
                log.warning(f"{file} is still in use")

    async def get_random_voice(self, **kwargs):
        voices = await self.voices
        return {
            **kwargs,
            "voice": random.choice(list(voices.values())),
            "pitch": random.uniform(-20, 20),
            "speaking_rate": random.uniform(0.85, 1.0),
        }


async def setup(bot) -> None:
    await bot.add_cog(Tts(bot))
