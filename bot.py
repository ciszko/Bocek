import os
from discord import state
from discord.ext.commands import Bot
import discord
from discord.utils import get
from dotenv import load_dotenv
import random
from datetime import timedelta, datetime
import re

from plugins.log import get_logger
from plugins.scrape import LolCounter
from plugins.tts import Tts
from plugins.anonse import Anonse
from plugins.rito import Rito
from plugins.glossary import Glossary

import platform
import asyncio
import pathlib
from difflib import get_close_matches

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('GUILD_ID')

log = get_logger(__name__)

if platform.system() == 'Windows':
    ffmpeg = 'D:/Projekt/Bocek/extras/ffmpeg.exe'
else:
    ffmpeg = '/usr/bin/ffmpeg'


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.glossary = Glossary(self, 'talk.json')
        self.rito = Rito()
        self.path = pathlib.Path(__file__).parent.absolute()
        self.channel_list = []
        self.voice_channel = '🍆💦💦💦💦'
        self.text_channel = 'piszemy'

        cogs = [LolCounter, Tts, Anonse]
        self.add_cogs(cogs)

        self.add_commands()

        self.bg_task = self.loop.create_task(self.random_check())
        self.rito_task = self.loop.create_task(self.rito_check())

    def add_cogs(self, cogs):
        # cog registration
        for cog in cogs:
            self.add_cog(cog(self))
            cog_name = re.sub(r'(?<!^)(?=[A-Z])', '_', cog.__name__).lower()
            setattr(self, cog_name, self.get_cog(cog_name))

    async def random_check(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for x in self.channel_list:
                if x.members and str(x.type) == 'voice' and not self.voice_clients:
                    # if len(x.members) > 0:
                    #     self.poll_task = self.loop.create_task(
                    #         self.random_poll(len(x.members)))
                    user = random.choice(x.members).name
                    all_users = ', '.join([m.name for m in x.members])
                    msg = self.glossary.get_random(
                        user=user, all_users=all_users)
                    tts = await self.tts.create_tts(msg, 'pl')
                    await self.play_on_channel(None, x, tts)
                    break

            wait_time = random.randint(5*60, 10*60)
            when_join = datetime.now() + timedelta(seconds=wait_time)
            log.info(f'Random join on {when_join.strftime("%H:%M:%S")}')

            activ_no = random.choice([0, 1, 2, 3, 5])
            activ = discord.Activity(
                type=activ_no,  name=self.glossary.get_random(f'activity_{activ_no}'))
            await self.change_presence(activity=activ)

            await asyncio.sleep(wait_time)

    async def random_poll(self, members):

        def get_likes(msg):
            # counts likes from messages
            like_emoji = 'thumbsup'
            if likes := [emoji for emoji in msg.reactions if emoji.name == like_emoji]:
                return likes[0].count
            return 0

        await self.wait_until_ready()

        log.info('Going into poll mode')
        poll_end = members * 60 * 2  # poll end
        end = datetime.now() + timedelta(seconds=poll_end)
        end = end.strftime('%H:%M:%S')
        to_send = f'Ankieta! Koniec o {end}'
        self.poll_msg = await self.text_channel.send(to_send)

        await asyncio.sleep(poll_end)

        scores = {k: get_likes(v) for k, v in self.poll_msgs.items()}
        best_author = max(scores, key=lambda x: scores[x])

        log.info(
            f'Poll has ended, best msg: {self.poll_msgs[best_author].content}')
        self.text_channel.send(
            f'Ankieta zakończona. Wygrał {best_author}')
        # reset poll variables
        self.poll_msgs = {}
        self.poll_msg = None
        return

    async def rito_check(self):
        await self.wait_until_ready()
        wait_time = 30
        while not self.is_closed():
            if in_game := await self.rito.in_game():
                wait_time = 10
                diff = await self.rito.compare_stats()
                if diff and random.random() < 0.3:
                    tts = await self.tts.create_tts(diff, 'pl')
                    await self.play_on_channel(None, self.voice_channel, tts)
            else:
                wait_time = 30
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

            to_say = self.glossary.get_random(
                'bocek_huju', user=message.author.name)
            tts = await self.tts.create_tts(to_say, 'pl')
            if hasattr(message.author.voice, 'channel') and message.author.voice.channel:
                await self.play_on_channel(message, message.author.voice.channel, tts)
            else:
                await message.add_reaction(self.get_emoji(283294977969356800))
                await message.reply(to_say)

        # elif hasattr(self.poll_msg) and hasattr(msg, 'reference') and msg.reference.message_id == self.poll_msg.id:
        #     self.poll_msgs[msg.author] = msg

        await self.process_commands(message)

    async def on_voice_state_update(self, member, before, after):
        if member == self.user:
            return
        if not hasattr(after, 'channel') and not hasattr(after.channel.name):
            return
        if before.channel != after.channel and after.channel == self.voice_channel:
            to_say = self.glossary.get_random('greetings', user=member.name)
            tts = await self.tts.create_tts(to_say, 'pl', random=True)
            await self.play_on_channel(None, after.channel, tts)

    async def play_on_channel(self, ctx=None, voice_channel=None, message=None):
        if self.voice_clients:
            return
        vc = await voice_channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable=ffmpeg, source=message))
        # Sleep while audio is playing.
        while vc.is_connected() and vc.is_playing():
            await asyncio.sleep(.1)
        try:
            await vc.disconnect()
        except Exception as e:
            log.info(e)
        else:
            try:
                await self.tts.delete_tts(message)
            except Exception:
                pass

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
            return await context.reply(f'Coś poszło nie tak, chyba się zebzdziałem 💩💩💩💩.\n Błąd: ``` {exception} ```')

    def add_commands(self):

        @self.command(name='siusiak', help='Powie Ci prawdę o siusiaku')
        async def siusiak(ctx):
            response = f'{ctx.author.name} ma {self.glossary.get_random("siusiak")} siusiaka'
            await ctx.send(response)
            await ctx.message.delete()


bot = MyBot(command_prefix='$')

bot.run(TOKEN)
