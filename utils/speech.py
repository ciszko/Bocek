from __future__ import annotations

import asyncio
import time
from collections import deque
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

    def playing(self) -> bool: ...

    async def connect(self) -> bool: ...

    async def play(
        self, path: Path, on_done: Callable[[], Awaitable[None]]
    ) -> bool: ...

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
        fart_pool_size: int = 3,
        fart_refill_delay: float = 1.0,
    ):
        self._synth = synthesizer
        self._output = output
        self._make_fart = make_fart
        self._audio_dir = audio_dir
        self._clock = clock
        self._pending: set[asyncio.Task] = set()
        self._farts: deque[Path] = deque()
        self._fart_pool_size = fart_pool_size
        self._fart_refill_delay = fart_refill_delay
        self._fart_refill: asyncio.Task | None = None

    async def say(
        self, text: str, voice: Voice = "default", delay: float = 0.0
    ) -> bool:
        """Speak `text`. `voice` is "default", "random" or synthesizer params.

        Synthesis and the voice connection run concurrently. `delay` holds
        playback back by that many seconds, counted from the call, while the
        audio is prepared meanwhile.

        Returns True if audio started playing. Drops (never queues) when
        nothing can listen or audio is already playing.
        """
        if not text or not await self._can_speak() or self._busy():
            return False
        timings = _Timings("say", self._clock)
        connect, hold = self._prepare(timings, delay)
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
            started = await self._play(path, timings, connect, hold)
            return started
        finally:
            self._settle(connect, hold)
            timings.log(started)

    async def fart(self) -> bool:
        if not await self._can_speak() or self._busy():
            return False
        timings = _Timings("fart", self._clock)
        connect, hold = self._prepare(timings, 0.0)
        started = False
        try:
            with timings.stage("fart"):
                path = await self._new_fart()
            started = await self._play(path, timings, connect, hold)
            return started
        finally:
            self._settle(connect, hold)
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
            await asyncio.to_thread(self._delete_all, set(self._farts))

    def warm_up(self) -> None:
        """Start preparing farts in the background so /pierd has one ready."""
        self._ensure_fart_refill()

    async def shutdown(self) -> None:
        if self._fart_refill:
            self._fart_refill.cancel()
        await self._output.disconnect()
        while self._farts:
            await self._delete(self._farts.popleft())

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
        path = self._farts.popleft() if self._farts else None
        if path is None:
            path = await asyncio.to_thread(self._make_fart)
        self._ensure_fart_refill()
        return path

    def _ensure_fart_refill(self) -> None:
        if self._fart_refill and not self._fart_refill.done():
            return
        self._fart_refill = asyncio.create_task(self._refill_farts())

    async def _refill_farts(self) -> None:
        try:
            while len(self._farts) < self._fart_pool_size:
                await asyncio.sleep(self._fart_refill_delay)
                self._farts.append(await asyncio.to_thread(self._make_fart))
        except Exception as e:
            log.exception(f"Preparing a fart failed: {e}")

    def _busy(self) -> bool:
        if self._output.playing():
            log.info("Already playing, dropping request")
            return True
        return False

    async def _can_speak(self) -> bool:
        if not self._output.ready:
            log.info("Bot not ready, skipping playback")
            return False
        if self._output.listeners() < 1:
            await self._output.disconnect()
            return False
        return True

    def _prepare(
        self, timings: _Timings, delay: float
    ) -> tuple[asyncio.Task, asyncio.Task | None]:
        async def connect() -> bool:
            with timings.stage("connect"):
                return await self._output.connect()

        connect_task = asyncio.create_task(connect())
        self._pending.add(connect_task)
        connect_task.add_done_callback(self._pending.discard)
        hold = asyncio.create_task(asyncio.sleep(delay)) if delay > 0 else None
        return connect_task, hold

    def _settle(self, connect: asyncio.Task, hold: asyncio.Task | None) -> None:
        # A started connection is left to finish so the next request reuses it.
        connect.add_done_callback(lambda t: t.cancelled() or t.exception())
        if hold:
            hold.cancel()

    async def _play(
        self,
        path: Path,
        timings: _Timings,
        connect: asyncio.Task,
        hold: asyncio.Task | None,
    ) -> bool:
        async def on_done():
            await self._delete(path)
            if self._output.listeners() < 1:
                await self._output.disconnect()

        started = False
        if await connect:
            if hold:
                await hold
            if hold is None or await self._can_speak():
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

    def _delete_all(self, keep: set[Path]) -> None:
        log.info("Deleting all speech audio")
        for file in self._audio_dir.iterdir():
            if file in keep:
                continue
            try:
                file.unlink()
            except PermissionError:
                log.warning(f"{file} is still in use")
