import asyncio
from functools import wraps, partial
import os
import pathlib
import random
from discord.ext.commands import Cog


BASEDIR = os.path.join(pathlib.Path(__file__).parent.absolute(), "..")


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


class MyCog(Cog):
    def get_rhyme(self, text):
        to_ret = ""
        if to_ret := self.bot.rhyme.get_rhyme(text):
            to_ret = random.choice(to_ret)
        return to_ret
