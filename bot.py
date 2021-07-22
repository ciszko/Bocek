import os
import re
from dotenv import load_dotenv

import discord
from discord.ext.commands import Bot

from plugins.log import get_logger
from plugins.lol_counter import LolCounter
from plugins.tts import Tts
from plugins.anonse import Anonse
from plugins.rito import Rito
from plugins.glossary import Glossary
from plugins.random_event import RandomEvent

import platform
import asyncio
import pathlib
from difflib import get_close_matches
from mutagen.ogg import OggFileType
from time import time

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('GUILD_ID')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(pathlib.Path(
    __file__).parent.absolute(), os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))

log = get_logger(__name__)

if platform.system() == 'Windows':
    ffmpeg = 'D:/Projekt/Bocek/extras/ffmpeg.exe'
else:
    ffmpeg = '/usr/bin/ffmpeg'


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.glossary = Glossary(self, 'talk.json')
        self.path = pathlib.Path(__file__).parent.absolute()
        self.channel_list = []
        self.voice_channel = '🍆💦💦💦💦'  # later changed to Channel object
        self.text_channel = 'piszemy'  # later changed to Channel object

        cogs = [LolCounter, Tts, Anonse, RandomEvent, Rito]
        self.add_cogs(cogs)

        self.add_commands()

        self.bg_task = self.loop.create_task(self.random_event.random_check())
        self.rito_task = self.loop.create_task(self.rito.rito_check())

    def add_cogs(self, cogs):
        # cog registration
        # name Cogs with PascalCase, then bot will have snake_case attribute
        # LolCounter -> self.lol_counter
        for cog in cogs:
            self.add_cog(cog(self))
            cog_name = re.sub(r'(?<!^)(?=[A-Z])', '_', cog.__name__).lower()
            setattr(self, cog_name, self.get_cog(cog_name))

    async def on_message(self, message):
        if message.author == self.user:
            return

        msg = message.content.lower()

        greetings = ['cześć bocek', 'czesc bocek',
                     'czesć bocek', 'cześc bocek']

        if any(x in msg for x in greetings):
            await message.channel.send(f'Siemano {message.author.name}!')

        elif msg == 'bocek huju':

            to_say = self.glossary.get_random(
                'bocek_huju', user=message.author.name)
            tts = await self.tts.create_tts(to_say, 'pl')
            if hasattr(message.author.voice, 'channel') and message.author.voice.channel:
                await self.play_on_channel(message.author.voice.channel, tts)
            else:
                await message.add_reaction(self.get_emoji(283294977969356800))
                await message.reply(to_say)

        await self.process_commands(message)

    async def on_voice_state_update(self, member, before, after):
        if member == self.user:
            return
        if not hasattr(after, 'channel') and not hasattr(after.channel.name):
            return
        if before.channel != after.channel and after.channel == self.voice_channel:
            to_say = self.glossary.get_random('greetings', user=member.name)
            tts = await self.tts.create_tts(to_say, 'pl', random=True)
            await self.play_on_channel(after.channel, tts)

    async def play_on_channel(self, voice_channel=None, message=None):
        if self.voice_clients:
            log.warning(f'Found voice clients: {self.voice_clients}')
            return
        vc = await voice_channel.connect()
        duration = OggFileType(message).info.lenght
        log.info(f'OGG duration: {duration}')
        vc.play(discord.FFmpegOpusAudio(executable=ffmpeg, source=message))
        timeout = time() + duration + 5  # timeout is audio duration + 5s
        # Sleep while audio is playing.
        while vc.is_connected() and vc.is_playing() and time() < timeout:
            await asyncio.sleep(.2)
        else:
            await asyncio.sleep(0.5)  # sometimes mp3 is still playing
            await vc.disconnect()
            await self.tts.delete_tts(message)

    async def on_ready(self):
        log.info(f'{self.user.name} has connected to Discord!')
        for channel in self.get_all_channels():
            self.channel_list.append(channel)
            if channel.name == self.voice_channel:
                self.voice_channel = channel
            elif channel.name == self.text_channel:
                self.text_channel = channel

    async def on_command_error(self, context, exception):
        if type(exception) == discord.ext.commands.errors.CommandNotFound:
            all_commands = [x.name for x in self.commands]
            msg = context.message
            closest_match = get_close_matches(
                msg.content, all_commands, n=1)
            await context.message.add_reaction('❓')
            if closest_match:
                return await msg.reply(f'Grube paluszki :( Czy chodziło Ci o **${closest_match[0]}**?')
            else:
                return await msg.reply(f'Masz tak grube paluszki, że nie wiem o co chodzi :(')
        else:
            log.exception(exception)
            return await context.reply(f'Coś poszło nie tak, chyba się zebzdziałem 💩💩💩💩.\nBłąd: ```{exception}```')

    def add_commands(self):

        @self.command(name='siusiak', help='Powie Ci prawdę o siusiaku')
        async def siusiak(ctx):
            response = f'{ctx.author.name} ma {self.glossary.get_random("siusiak")} siusiaka'
            await ctx.send(response)
            await ctx.message.delete()


bot = MyBot(command_prefix='$')

bot.run(TOKEN)
