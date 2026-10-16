from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

from utils.log import log


class SynthesisUnavailable(Exception):
    """The synthesizer is temporarily down; Speech falls back to a fart."""


class Synthesizer(Protocol):
    async def synthesize(self, text: str, **params) -> Path | None: ...

    async def random_voice(self) -> dict: ...

    async def voices(self) -> dict[str, str]: ...


class VoiceOutput(Protocol):
    @property
    def ready(self) -> bool: ...

    def listeners(self) -> int: ...

    async def play(self, path: Path, on_done: Callable[[], Awaitable[None]]) -> bool: ...

    def stop(self) -> bool: ...

    async def disconnect(self) -> None: ...


Voice = str | dict


class Speech:
    """Text to audio to the voice channel; owns the lifetime of temp audio files."""

    def __init__(
        self,
        synthesizer: Synthesizer,
        output: VoiceOutput,
        make_fart: Callable[[], Path],
        audio_dir: Path,
    ):
        self._synth = synthesizer
        self._output = output
        self._make_fart = make_fart
        self._audio_dir = audio_dir

    async def say(self, text: str, voice: Voice = "default") -> bool:
        """Speak `text`. `voice` is "default", "random" or synthesizer params.

        Returns True if audio started playing. Drops (never queues) when
        nothing can listen or audio is already playing.
        """
        if not text or not await self._can_speak():
            return False
        try:
            path = await self._synthesize(text, voice)
        except SynthesisUnavailable:
            path = await self._new_fart()
        if path is None:
            return False
        return await self._play(path)

    async def fart(self) -> bool:
        if not await self._can_speak():
            return False
        return await self._play(await self._new_fart())

    async def synthesize(self, text: str, **params) -> Path | None:
        """Render to a file without playing it; the caller owns the file."""
        try:
            return await self._synthesize(text, params)
        except SynthesisUnavailable:
            return None

    async def voices(self) -> dict[str, str]:
        return await self._synth.voices()

    def stop(self) -> bool:
        return self._output.stop()

    async def leave_if_empty(self) -> None:
        if self._output.listeners() < 1:
            await self._output.disconnect()
            await asyncio.to_thread(self._delete_all)

    async def shutdown(self) -> None:
        await self._output.disconnect()

    async def _synthesize(self, text: str, voice: Voice) -> Path | None:
        if voice == "default":
            params = {}
        elif voice == "random":
            params = await self._synth.random_voice()
        else:
            params = voice
        log.info(f"Speech text={text} params={params}")
        return await self._synth.synthesize(text, **params)

    async def _new_fart(self) -> Path:
        return await asyncio.to_thread(self._make_fart)

    async def _can_speak(self) -> bool:
        if not self._output.ready:
            log.info("Bot not ready, skipping playback")
            return False
        if self._output.listeners() < 1:
            await self._output.disconnect()
            return False
        return True

    async def _play(self, path: Path) -> bool:
        async def on_done():
            await self._delete(path)
            if self._output.listeners() < 1:
                await self._output.disconnect()

        started = await self._output.play(path, on_done)
        if not started:
            await self._delete(path)
        return started

    async def _delete(self, path: Path) -> None:
        try:
            await asyncio.to_thread(Path(path).unlink)
            log.info(f"Removed {path}")
        except FileNotFoundError:
            log.warning(f"{path} was already deleted")

    def _delete_all(self) -> None:
        log.info("Deleting all speech audio")
        for file in self._audio_dir.iterdir():
            try:
                file.unlink()
            except PermissionError:
                log.warning(f"{file} is still in use")
