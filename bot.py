import os
from discord.ext.commands import Bot
from discord.ext import commands
from discord.utils import get
import discord
from dotenv import load_dotenv
import random
from plugins.scrape import LolCounter
from plugins.tts import TTS
from plugins.anonse import Anonse
from plugins.rito import Rito
import platform
import asyncio
import pathlib

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('GUILD_ID')

if platform.system() == 'Windows':
    ffmpeg = 'D:/Projekt/Bocek/extras/ffmpeg.exe'
else:
    ffmpeg = '/usr/bin/ffmpeg'


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lol_counter = LolCounter()
        self.gtts = TTS()
        self.anonse = Anonse()
        self.rito = Rito()
        self.channel_list = []
        self.path = pathlib.Path(__file__).parent.absolute()

        self.bg_task = self.loop.create_task(self.random_msg())
        self.rito_task = self.loop.create_task(self.rito_check())

        self.add_commands()

    async def random_msg(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for x in self.channel_list:
                if x.members and str(x.type) == 'voice' and not self.voice_clients:
                    msg = self.get_random_join_msg()
                    msg = msg.replace('%user%', random.choice(x.members).name)
                    msg = msg.replace('%all%', ', '.join(
                        [m.name for m in x.members]))
                    tts = self.gtts.create_tts(msg, 'pl')
                    await self.play_on_channel(None, x, tts)
                    break
            # task runs every 60 seconds
            await asyncio.sleep(random.randint(10*60, 15*60))

    def get_random_join_msg(self):
        file_path = os.path.join(self.path, 'glossary/random_join.txt')
        with open(file_path, 'r+', encoding="utf-8") as f:
            lines = f.readlines()
        index = random.randrange(len(lines))
        print(index)
        return lines[index]

    async def rito_check(self):
        await self.wait_until_ready()
        wait_time = 30
        while not self.is_closed():
            if in_game := await self.rito.in_game():
                wait_time = 10
                diff = await self.rito.compare_stats()
                print(diff)
            else:
                print(in_game)
            await asyncio.sleep(wait_time)

    async def on_message(self, message):
        if message.author == self.user:
            return

        msg = message.content.lower()

        greetings = ['cześć bocek', 'czesc bocek',
                     'czesć bocek', 'cześc bocek']

        if any(x in msg for x in greetings):
            await message.channel.send(f'Siemano {message.author.name}!')

        elif msg == 'bocek huju':
            to_choose = ['paruwo', 'obżydronie', 'obszczańcu', 'kutfo']
            to_choose_2 = [message.author.name, 'ty']

            to_say = f'{random.choice(to_choose_2)} {random.choice(to_choose)}'
            tts = self.gtts.create_tts(to_say, 'pl')
            if message.author.voice.channel:
                await self.play_on_channel(message, message.author.voice.channel, tts)
            else:
                await message.channel.send(f'{message.author.name} {random.choice(to_choose)}', tts=True)

        await self.process_commands(message)

    async def play_on_channel(self, ctx=None, voice_channel=None, message=None):
        vc = await voice_channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable=ffmpeg, source=message))
        # Sleep while audio is playing.
        while vc.is_connected() and vc.is_playing():
            await asyncio.sleep(.2)
        try:
            await vc.disconnect()
        except Exception as e:
            print(e)

        # Delete command after the audio is done playing.
        if not ctx:
            return
        if hasattr(ctx, 'message'):
            await ctx.message.delete()
        else:
            await ctx.delete()

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord!')
        for channel in self.get_all_channels():
            self.channel_list.append(channel)

    def add_commands(self):

        @self.command(name='siusiak', help='Powie Ci prawdę o siusiaku')
        async def siusiak(ctx):
            types = ['potężnego', 'małego', 'brudnego',
                     'paskudnego', 'ślicznego', 'krzywego', 'obszczanego']
            response = f'{ctx.author.name} ma {random.choice(types)} siusiaka'
            await ctx.send(response)
            await ctx.message.delete()

        @self.command(name='counter', help='Zwraca x kontr na daną postać: $counter jinx x')
        async def counter(ctx, *arg):
            counters = self.lol_counter.get_lol_counters(*arg)
            response = f'**Kontry na {arg[0]}:**\n'
            response += '\n'.join(f'{x}: {y}' for x, y in counters)
            await ctx.send(response)
            await ctx.message.delete()

        @self.command(name='tts', help='Zwraca plik z nagraniem: $tts "tutaj tekst"')
        async def tts(ctx, arg):
            tts = self.gtts.create_tts(arg, 'pl')

            await ctx.send(file=discord.File(tts))
            await ctx.message.delete()

        @self.command(name='anonse', help='Zwraca losowe gejowe anonse')
        async def anonse(ctx, arg='fetysze'):
            # Gets voice channel of message author
            if voice := ctx.author.voice:
                voice_channel = voice.channel
                msg = self.anonse.get_anonse(arg)
                tts = self.gtts.create_tts(msg, 'pl')
                await self.play_on_channel(ctx, voice_channel, tts)
            else:
                msg = (f'{ctx.author.name}, nie jesteś nawet na kanale...')
                await ctx.channel.send(msg)


bot = MyBot(command_prefix='$')

channel_list = []


bot.run(TOKEN)
