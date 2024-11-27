import asyncio
import os
import pathlib
import platform
import random
from functools import partial, wraps

from discord.ext.commands import Bot
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("GUILD_ID")
BASE_DIR = pathlib.Path(__file__).parent.parent
MP3_DIR = BASE_DIR / "mp3"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
    BASE_DIR / os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
)
if platform.system() == "Windows":
    FFMPEG = "D:/Projekt/Bocek/extras/ffmpeg.exe"
else:
    FFMPEG = "/usr/bin/ffmpeg"


def async_wrap(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)

    return run


def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


class RhymeExtension:
    def get_rhyme(self, text):
        to_ret = ""
        ctx = self if isinstance(self, Bot) else self.bot
        if to_ret := ctx.get_cog("rhyme").get_rhyme(text):
            to_ret = random.choice(to_ret)
        return to_ret
