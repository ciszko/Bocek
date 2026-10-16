import asyncio

import pytest

from utils.speech import Speech, SynthesisUnavailable


class FakeSynthesizer:
    def __init__(self, audio_dir):
        self.audio_dir = audio_dir
        self.calls = []
        self.unavailable = False
        self.fail_with_none = False

    async def synthesize(self, text, **params):
        self.calls.append((text, params))
        if self.unavailable:
            raise SynthesisUnavailable
        if self.fail_with_none:
            return None
        path = self.audio_dir / f"say_{len(self.calls)}.mp3"
        path.write_bytes(b"x")
        return path

    async def random_voice(self):
        return {"voice": "random-voice"}

    async def voices(self):
        return {"v": "v"}


class RecordingOutput:
    def __init__(self):
        self.ready = True
        self.humans = 1
        self.busy = False
        self.played = []
        self.disconnects = 0
        self.connects = 0
        self.connected = True
        self._on_done = None

    def listeners(self):
        return self.humans

    async def connect(self):
        self.connects += 1
        return self.connected

    async def play(self, path, on_done):
        if self.busy:
            return False
        self.played.append(path)
        self._on_done = on_done
        return True

    def stop(self):
        return bool(self.played)

    async def disconnect(self):
        self.disconnects += 1

    async def finish_playback(self):
        await self._on_done()


@pytest.fixture
def audio_dir(tmp_path):
    return tmp_path


@pytest.fixture
def synth(audio_dir):
    return FakeSynthesizer(audio_dir)


@pytest.fixture
def output():
    return RecordingOutput()


@pytest.fixture
def speech(synth, output, audio_dir):
    def make_fart():
        path = audio_dir / "fart_1.mp3"
        path.write_bytes(b"f")
        return path

    return Speech(synth, output, make_fart, audio_dir)


async def test_say_plays_synthesized_audio(speech, synth, output):
    assert await speech.say("hello") is True
    assert synth.calls == [("hello", {})]
    assert len(output.played) == 1


async def test_say_random_voice_uses_synthesizer_params(speech, synth):
    await speech.say("hello", voice="random")
    assert synth.calls == [("hello", {"voice": "random-voice"})]


async def test_say_does_nothing_when_not_ready(speech, synth, output):
    output.ready = False
    assert await speech.say("hello") is False
    assert synth.calls == [] and output.played == []


async def test_say_does_nothing_without_listeners(speech, synth, output):
    output.humans = 0
    assert await speech.say("hello") is False
    assert synth.calls == [] and output.played == []
    assert output.disconnects == 1


async def test_say_empty_text_is_ignored(speech, output):
    assert await speech.say("") is False
    assert output.played == []


async def test_say_drops_and_cleans_up_when_already_playing(speech, output, audio_dir):
    output.busy = True
    assert await speech.say("hello") is False
    assert list(audio_dir.iterdir()) == []


async def test_say_falls_back_to_fart_when_synthesis_unavailable(speech, synth, output):
    synth.unavailable = True
    assert await speech.say("hello") is True
    assert output.played[0].name.startswith("fart_")


async def test_temp_file_deleted_after_playback(speech, output, audio_dir):
    await speech.say("hello")
    assert len(list(audio_dir.iterdir())) == 1
    await output.finish_playback()
    assert list(audio_dir.iterdir()) == []


async def test_fart_file_deleted_after_playback(speech, output, audio_dir):
    assert await speech.fart() is True
    await output.finish_playback()
    assert list(audio_dir.iterdir()) == []


async def test_disconnects_after_playback_when_channel_emptied(speech, output):
    await speech.say("hello")
    output.humans = 0
    await output.finish_playback()
    assert output.disconnects == 1


async def test_synthesize_returns_file_without_playing(speech, output):
    path = await speech.synthesize("hello", pitch=1)
    assert path is not None and path.exists()
    assert output.played == []


async def test_synthesize_returns_none_when_unavailable(speech, synth):
    synth.unavailable = True
    assert await speech.synthesize("hello") is None


async def test_leave_if_empty_disconnects_and_clears_files(speech, output, audio_dir):
    (audio_dir / "old.mp3").write_bytes(b"x")
    output.humans = 0
    await speech.leave_if_empty()
    assert output.disconnects == 1
    assert list(audio_dir.iterdir()) == []


async def test_leave_if_empty_noop_with_listeners(speech, output, audio_dir):
    (audio_dir / "old.mp3").write_bytes(b"x")
    await speech.leave_if_empty()
    assert output.disconnects == 0
    assert len(list(audio_dir.iterdir())) == 1


class StepClock:
    def __init__(self, step=0.5):
        self.now = 0.0
        self.step = step

    def __call__(self):
        self.now += self.step
        return self.now


@pytest.fixture
def log_lines():
    from utils.log import log

    lines = []
    sink = log.add(lambda m: lines.append(m.record["message"]), level="INFO")
    yield lines
    log.remove(sink)


async def test_say_logs_one_timing_line_with_stages(
    synth, output, audio_dir, log_lines
):
    speech = Speech(synth, output, lambda: None, audio_dir, clock=StepClock())
    await speech.say("hello")
    lines = [m for m in log_lines if m.startswith("Speech say:")]
    assert len(lines) == 1
    assert "synth=0.50s connect=0.50s play=0.50s" in lines[0]
    assert "started=True" in lines[0]


async def test_fart_logs_timing_line(speech, log_lines):
    await speech.fart()
    lines = [m for m in log_lines if m.startswith("Speech fart:")]
    assert len(lines) == 1
    assert "fart=" in lines[0] and "connect=" in lines[0]


async def test_timing_line_logged_when_connect_fails(
    speech, output, audio_dir, log_lines
):
    output.connected = False
    assert await speech.say("hello") is False
    assert output.played == []
    assert list(audio_dir.iterdir()) == []
    assert any("started=False" in m for m in log_lines)


class GatedOutput(RecordingOutput):
    """connect() only finishes once released; records when it was started."""

    def __init__(self):
        super().__init__()
        self.connect_started = asyncio.Event()
        self.release_connect = asyncio.Event()

    async def connect(self):
        self.connect_started.set()
        await self.release_connect.wait()
        return await super().connect()


async def test_synthesis_runs_while_connecting(synth, audio_dir):
    output = GatedOutput()
    speech = Speech(synth, output, lambda: None, audio_dir)
    task = asyncio.create_task(speech.say("hello"))
    await asyncio.wait_for(output.connect_started.wait(), 1)
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert synth.calls == [("hello", {})]
    assert output.played == []
    output.release_connect.set()
    assert await asyncio.wait_for(task, 1) is True


async def test_connection_runs_while_synthesis_in_flight(audio_dir, output):
    release = asyncio.Event()

    class SlowSynth(FakeSynthesizer):
        async def synthesize(self, text, **params):
            await release.wait()
            return await super().synthesize(text, **params)

    speech = Speech(SlowSynth(audio_dir), output, lambda: None, audio_dir)
    task = asyncio.create_task(speech.say("hello"))
    await asyncio.sleep(0.01)
    assert output.connects == 1
    release.set()
    assert await asyncio.wait_for(task, 1) is True


async def test_failed_connect_drops_synthesized_file(speech, output, audio_dir):
    output.connected = False
    assert await speech.say("hello") is False
    assert list(audio_dir.iterdir()) == []


async def test_synthesis_failure_still_lets_connection_finish(speech, synth, output):
    synth.fail_with_none = True
    assert await speech.say("hello") is False
    await asyncio.sleep(0.01)
    assert output.connects == 1


async def test_delay_holds_playback_but_not_synthesis(speech, synth, output):
    loop = asyncio.get_running_loop()
    start = loop.time()
    assert await speech.say("hello", delay=0.1) is True
    assert synth.calls
    assert loop.time() - start >= 0.1


async def test_delay_does_not_slow_down_when_audio_is_slower(synth, output, audio_dir):
    class SlowSynth(FakeSynthesizer):
        async def synthesize(self, text, **params):
            await asyncio.sleep(0.15)
            return await super().synthesize(text, **params)

    speech = Speech(SlowSynth(audio_dir), output, lambda: None, audio_dir)
    loop = asyncio.get_running_loop()
    start = loop.time()
    await speech.say("hello", delay=0.1)
    assert loop.time() - start < 0.22


async def test_listener_leaving_during_delay_drops_audio(speech, output, audio_dir):
    task = asyncio.create_task(speech.say("hello", delay=0.1))
    await asyncio.sleep(0.02)
    output.humans = 0
    assert await task is False
    assert output.played == []
    assert output.disconnects >= 1
    assert list(audio_dir.iterdir()) == []
