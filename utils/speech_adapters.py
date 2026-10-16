from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from pathlib import Path
from time import time
from typing import TYPE_CHECKING
from uuid import uuid4

import discord
from google.api_core.exceptions import InvalidArgument, ServiceUnavailable
from google.cloud import texttospeech
from pydub import AudioSegment, effects

from utils.common import BASE_DIR, FFMPEG, FFPMEG_OPTIONS, MP3_DIR
from utils.log import log
from utils.speech import SynthesisUnavailable

if TYPE_CHECKING:
    from bot import MyBot


class GoogleSynthesizer:
    def __init__(self, audio_dir: Path = MP3_DIR):
        self._audio_dir = audio_dir
        self._client = texttospeech.TextToSpeechAsyncClient()
        self._voices: dict[str, str] | None = None

    async def voices(self) -> dict[str, str]:
        if self._voices is None:
            resp = await self._client.list_voices(language_code="pl-PL")
            self._voices = {
                f"{v.name}-{v.ssml_gender.name}": v.name
                for v in resp.voices
                if "F" not in v.name
            }
        return self._voices

    async def random_voice(self) -> dict:
        voices = await self.voices()
        return {
            "voice": random.choice(list(voices.values())),
            "pitch": random.uniform(-20, 20),
            "speaking_rate": random.uniform(0.85, 1.0),
        }

    async def synthesize(
        self,
        text,
        pitch=0.0,
        voice="pl-PL-Wavenet-B",
        volume=0.0,
        speaking_rate=0.9,
        lang="pl-PL",
    ) -> Path | None:
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
            try:
                response = await self._client.synthesize_speech(
                    input=tts_input, voice=voice_params, audio_config=audio_config
                )
            except InvalidArgument:
                audio_config.speaking_rate = None
                audio_config.pitch = None
                response = await self._client.synthesize_speech(
                    input=tts_input, voice=voice_params, audio_config=audio_config
                )
        except ServiceUnavailable as exc:
            self._voices = None
            raise SynthesisUnavailable from exc
        except Exception as exc:
            log.exception(f"TTS synthesis failed: {exc}")
            return None
        if response is None:
            return None
        path = self._audio_dir / f"{uuid4().hex[:10]}.mp3"
        path.write_bytes(response.audio_content)
        return path


class DiscordVoiceOutput:
    def __init__(self, bot: MyBot):
        self._bot = bot
        self._vc: discord.VoiceClient | None = None
        self._is_connecting = False

    @property
    def ready(self) -> bool:
        return self._bot.ready

    def listeners(self) -> int:
        channel = self._bot.voice_channel
        return len([m for m in channel.members if not m.bot]) if channel else 0

    def playing(self) -> bool:
        return bool(self._vc and self._vc.is_playing())

    async def connect(self) -> bool:
        if self._is_connecting:
            log.warning("Already attempting to connect to voice channel")
            return False
        return await self._ensure_connected()

    async def play(self, path: Path, on_done: Callable[[], Awaitable[None]]) -> bool:
        if not self._vc or not self._vc.is_connected():
            return False
        if self._vc.is_playing():
            log.warning("Already playing")
            return False

        def after(error):
            if error:
                log.error(f"Playback error: {error}")
            asyncio.run_coroutine_threadsafe(on_done(), self._bot.loop)

        try:
            log.info(f"Playing audio: {path}")
            source = await asyncio.to_thread(
                discord.FFmpegOpusAudio,
                executable=FFMPEG,
                source=str(path),
                options=FFPMEG_OPTIONS,
            )
            self._vc.play(source, after=after)
        except discord.errors.ClientException as e:
            log.error(f"Failed to play audio: {e}")
            return False
        return True

    def stop(self) -> bool:
        if self._vc and self._vc.is_playing():
            self._vc.stop()
            return True
        return False

    async def disconnect(self) -> None:
        if not self._bot.voice_clients and not self._vc:
            return
        log.info("DISCONNECTING FROM VOICE")
        for vc in self._bot.voice_clients:
            await vc.disconnect(force=True)
        self._vc = None

    async def _ensure_connected(self) -> bool:
        if self._vc and self._vc.is_connected():
            return True
        start = time()
        try:
            self._is_connecting = True
            log.info("Connecting to voice channel")
            self._vc = await asyncio.wait_for(
                self._bot.voice_channel.connect(), timeout=6
            )
            log.info(f"Voice connection took {time() - start:.2f}s")
        except asyncio.TimeoutError:
            log.error("Voice connection timed out")
            return False
        except discord.ClientException as e:
            log.warning(f"Voice connection error: {e}")
            await self.disconnect()
            try:
                self._vc = await asyncio.wait_for(
                    self._bot.voice_channel.connect(), timeout=6
                )
                log.info(f"Reconnection took {time() - start:.2f}s")
            except Exception as e:
                log.error(f"Failed to reconnect: {e}")
                return False
        finally:
            self._is_connecting = False
        return True


def make_fart() -> Path:
    source = random.choice(list((BASE_DIR / "farts").iterdir()))
    audio = _apply_random_fart_effects(AudioSegment.from_mp3(source))
    out_path = MP3_DIR / f"fart_{uuid4().hex[:8]}.mp3"
    audio.export(out_path, format="mp3")
    return out_path.absolute()


def _apply_random_fart_effects(audio: AudioSegment) -> AudioSegment:
    # pitch shift via frame rate trick (range: 0.3x–1.9x of original)
    pitch_factor = random.uniform(0.3, 1.9)
    shifted = audio._spawn(
        audio.raw_data,
        overrides={"frame_rate": int(audio.frame_rate * pitch_factor)},
    ).set_frame_rate(audio.frame_rate)

    # random speed stretch (0.8x–1.4x), independent of pitch
    speed_factor = random.uniform(0.8, 1.4)
    if speed_factor != 1.0:
        shifted = (
            effects.speedup(shifted, playback_speed=speed_factor)
            if speed_factor > 1.0
            else shifted._spawn(
                shifted.raw_data,
                overrides={"frame_rate": int(shifted.frame_rate * speed_factor)},
            ).set_frame_rate(shifted.frame_rate)
        )

    # optional reverb: mix in 2 decaying echoes
    if random.random() < 0.5:
        delay_ms = random.randint(80, 250)
        decay = random.uniform(0.25, 0.5)
        echo1 = shifted - (shifted.dBFS * (1 - decay) + 6)
        echo2 = shifted - (shifted.dBFS * (1 - decay * 0.5) + 10)
        padded = shifted + AudioSegment.silent(duration=delay_ms * 2)
        padded = padded.overlay(echo1, position=delay_ms)
        padded = padded.overlay(echo2, position=delay_ms * 2)
        shifted = padded

    # slight volume randomness ±4 dB
    return shifted + random.uniform(-4, 4)
