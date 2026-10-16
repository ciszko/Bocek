import os
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import discord

from utils.speech_adapters import DiscordVoiceOutput


class FakeVC:
    def __init__(self):
        self.played = None

    def is_connected(self):
        return True

    def is_playing(self):
        return False

    def play(self, source, after=None):
        self.played = source


async def test_playback_source_is_created_off_the_event_loop(monkeypatch):
    threads = []

    def fake_source(**kwargs):
        threads.append(threading.current_thread())
        return "source"

    monkeypatch.setattr(discord, "FFmpegOpusAudio", fake_source)
    output = DiscordVoiceOutput(SimpleNamespace(loop=None))
    output._vc = FakeVC()

    assert await output.play(Path("a.mp3"), lambda: None) is True
    assert output._vc.played == "source"
    assert threads and threads[0] is not threading.main_thread()


def test_grpc_fork_support_is_disabled_by_default():
    env = {k: v for k, v in os.environ.items() if k != "GRPC_ENABLE_FORK_SUPPORT"}
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import utils.common, os; print(os.environ['GRPC_ENABLE_FORK_SUPPORT'])",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert out.stdout.strip() == "0", out.stderr
