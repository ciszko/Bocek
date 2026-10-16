from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
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

    async def connect(self) -> bool: ...

    async def play(self, path: Path, on_done: Callable[[], Awaitable[None]]) -> bool: ...

    def stop(self) -> bool: ...

    async def disconnect(self) -> None: ...


Voice = str | dict


class _Timings:
    """Named stage durations for one request, rendered as a single log line."""

    def __init__(self, kind: str, clock: Callable[[], float]):
        self._kind = kind
        self._clock = clock
        self._start = clock()
        self._stages: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str):
        start = self._clock()
        try:
            yield
        finally:
            self._stages[name] = self._stages.get(name, 0.0) + self._clock() - start

    def log(self, started: bool) -> None:
        stages = " ".join(f"{k}={v:.2f}s" for k, v in self._stages.items())
        total = self._clock() - self._start
        log.info(f"Speech {self._kind}: {stages} total={total:.2f}s started={started}")


class Speech:
    """Text to audio to the voice channel; owns the lifetime of temp audio files."""

    def __init__(
        self,
        synthesizer: Synthesizer,
        output: VoiceOutput,
        make_fart: Callable[[], Path],
        audio_dir: Path,
        clock: Callable[[], float] = time.perf_counter,
    ):
        self._synth = synthesizer
        self._output = output
        self._make_fart = make_fart
        self._audio_dir = audio_dir
        self._clock = clock

    async def say(self, text: str, voice: Voice = "default") -> bool:
        """Speak `text`. `voice` is "default", "random" or synthesizer params.

        Returns True if audio started playing. Drops (never queues) when
        nothing can listen or audio is already playing.
        """
        if not text or not await self._can_speak():
            return False
        timings = _Timings("say", self._clock)
        started = False
        try:
            try:
                with timings.stage("synth"):
                    path = await self._synthesize(text, voice)
            except SynthesisUnavailable:
                with timings.stage("fart"):
                    path = await self._new_fart()
            if path is None:
                return False
            started = await self._play(path, timings)
            return started
        finally:
            timings.log(started)

    async def fart(self) -> bool:
        if not await self._can_speak():
            return False
        timings = _Timings("fart", self._clock)
        started = False
        try:
            with timings.stage("fart"):
                path = await self._new_fart()
            started = await self._play(path, timings)
            return started
        finally:
            timings.log(started)

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

    async def _play(self, path: Path, timings: _Timings) -> bool:
        async def on_done():
            await self._delete(path)
            if self._output.listeners() < 1:
                await self._output.disconnect()

        with timings.stage("connect"):
            connected = await self._output.connect()
        started = False
        if connected:
            with timings.stage("play"):
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
