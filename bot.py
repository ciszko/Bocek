import os
import re
import random
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext.commands import Bot

from plugins.common import replace_all, BASE_DIR
from plugins.log import log
from plugins.lol_counter import LolCounter
from plugins.tts import Tts
from plugins.anonse import Anonse
from plugins.rito import Rito
from plugins.glossary import Glossary
from plugins.random_event import RandomEvent
from plugins.joke import Joke
from plugins.rhyme import Rhyme
from plugins.slang import Slang
from plugins.minecraft import Minecraft

import platform
import asyncio
from difflib import get_close_matches
from mutagen.mp3 import MP3
from time import time

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("GUILD_ID")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(
    BASE_DIR / os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
)

if platform.system() == "Windows":
    ffmpeg = "D:/Projekt/Bocek/extras/ffmpeg.exe"
else:
    ffmpeg = "/usr/bin/ffmpeg"


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ready = False
        self.glossary = Glossary(self, "talk.json")
        self.channel_list = []
        self.voice_channel_id = 283292201579184128
        self.text_channel_id = 283292201109159947
        self.vc = None

    async def setup_hook(self):
        cogs = [
            LolCounter,
            Tts,
            Anonse,
            RandomEvent,
            Rito,
            Joke,
            Rhyme,
            Slang,
            Minecraft,
        ]

        await self.add_cogs(cogs)
        self.add_commands()

        self.bg_task = self.loop.create_task(self.random_event.random_check())
        self.rito_task = self.loop.create_task(self.rito.rito_check())

        guild = discord.Object(id=GUILD)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    @property
    def voice_channel(self):
        return next(
            (c for c in self.channel_list if c.id == self.voice_channel_id), None
        )

    @property
    def text_channel(self):
        return next((c for c in self.channel_list if c.id == self.id), None)

    async def add_cogs(self, cogs):
        # cog registration
        # name Cogs with PascalCase, then bot will have snake_case attribute
        # LolCounter -> self.lol_counter
        for cog in cogs:
            await self.add_cog(cog(self))
            cog_name = cog.__cog_name__
            setattr(self, cog_name, self.get_cog(cog_name))
            log.info(f"Registered {cog.__name__} as a cog")

    def get_rhyme(self, text):
        to_ret = ""
        if to_ret := self.rhyme.get_rhyme(text):
            to_ret = random.choice(to_ret)
        return to_ret

    async def on_message(self, message):
        if message.author == self.user:
            return

        msg = message.content.lower()

        greetings = ["cześć bocek", "czesc bocek", "czesć bocek", "cześc bocek"]

        if any(x in msg for x in greetings):
            await message.channel.send(f"Siemano {message.author.name}!")

        elif msg == "bocek huju":
            to_say, placeholders = self.glossary.get_random("bocek_huju")
            user = message.author.name
            scope = locals()
            to_say = replace_all(
                to_say, {f"{{{p}}}": eval(p, scope) for p in placeholders}
            )

            tts = await self.tts.create_tts(to_say)
            if (
                hasattr(message.author.voice, "channel")
                and message.author.voice.channel
            ):
                await self.play_on_channel(tts)
            else:
                await message.add_reaction(self.get_emoji(283294977969356800))
                await message.reply(to_say)

        await self.process_commands(message)

    async def on_voice_state_update(self, member: discord.Member, before, after):
        if member == self.user or not self.ready:
            return
        if not hasattr(after, "channel") and not hasattr(after.channel.name):
            return
        if before.channel != after.channel and after.channel == self.voice_channel:
            await asyncio.sleep(0.75)
            to_say, placeholders = self.glossary.get_random("greetings")
            user = member.display_name if member.display_name else member.name
            scope = locals()
            to_say = replace_all(
                to_say, {f"{{{p}}}": eval(p, scope) for p in placeholders}
            )
            tts = await self.tts.create_tts(to_say, random=True)
            await self.play_on_channel(tts)
        if (
            after.channel != self.voice_channel
            and len(self.voice_channel.members) <= 1
            and self.vc
        ):
            await self.disconnect_from_voice()
            await self.tts.delete_all_tts()

    async def disconnect_from_voice(self):
        [
            await vc.disconnect(force=True)
            for vc in self.voice_clients
            if not vc.is_playing()
        ]
        self.vc = None

    async def play_on_channel(self, message=None):
        # if self.voice_clients:
        #     log.warning(f'Found voice clients: {self.voice_clients}')
        #     return
        if not self.ready:
            return
        if len(self.voice_channel.members) <= 1 and self.vc:
            try:
                await self.disconnect_from_voice()
            except Exception as e:
                log.exception(e)
            return
        if not self.vc:
            try:
                self.vc = await self.voice_channel.connect()
            except discord.ClientException:
                log.error("Already connected to voice channel")
                await self.disconnect_from_voice()
                self.vc = await self.voice_channel.connect()
        if self.vc and self.vc.is_playing():
            log.error("Already playing")
            return
        duration = MP3(message).info.length
        try:
            self.vc.play(
                discord.FFmpegOpusAudio(
                    executable=ffmpeg, source=message, options="-loglevel panic"
                )
            )
        except discord.errors.ClientException:
            log.error("Got disconnected from the channel")
            self.vc = await self.voice_channel.connect()
            self.vc.play(
                discord.FFmpegOpusAudio(
                    executable=ffmpeg, source=message, options="-loglevel panic"
                )
            )
        timeout = time() + duration + 1  # timeout is audio duration + 1s
        # Sleep while audio is playing.
        while self.vc and self.vc.is_playing() and time() < timeout:
            await asyncio.sleep(0.1)
        else:
            await asyncio.sleep(0.5)  # sometimes mp3 is still playing
            # await self.vc.disconnect()
        await self.tts.delete_tts(message)

    async def on_ready(self):
        self.channel_list = [c for c in self.get_all_channels()]
        self.ready = True
        log.info(f"{self.user.name} has connected to Discord!")

    async def on_command_error(self, context, exception):
        if type(exception) == discord.ext.commands.errors.CommandNotFound:
            all_commands = [x.name for x in self.commands]
            msg = context.message
            closest_match = get_close_matches(msg.content, all_commands, n=1)
            await context.message.add_reaction("❓")
            if closest_match:
                return await msg.reply(
                    f"Grube paluszki :( Czy chodziło Ci o **/{closest_match[0]}**?"
                )
            else:
                return await msg.reply(
                    f"Masz tak grube paluszki, że nie wiem o co chodzi :("
                )
        else:
            log.exception(exception)
            return await context.reply(
                "Coś poszło nie tak, chyba się zebzdziałem :shaking_face:."
                "Błąd:\n"
                f"```{exception}```"
            )

    def add_commands(self):
        @self.tree.command(name="siusiak", description="powie prawde o siusiaku")
        async def siusiak(interaction: discord.Interaction):
            """/siusiak"""
            siusiak, _ = self.glossary.get_random("siusiak")
            response = f"{interaction.user.name} ma {siusiak} siusiaka"
            await interaction.response.defer()
            if (
                hasattr(interaction.user.voice, "channel")
                and interaction.user.voice.channel
            ):
                tts = await self.tts.create_tts(response, random=True)
                await self.play_on_channel(tts)
            await interaction.followup.send(response)

        @self.tree.command(name="anus", description="anus anus nostradamus")
        async def anus(interaction: discord.Interaction):
            to_say = f"anus anus nostradamus"
            await interaction.response.defer(ephemeral=True)
            if (
                hasattr(interaction.user.voice, "channel")
                and interaction.user.voice.channel
            ):
                tts = await self.tts.create_tts(to_say, random=True)
                await self.play_on_channel(tts)
            await interaction.followup.send("anus")


intents = discord.Intents.all()
bot = MyBot(command_prefix="$", intents=intents)

bot.run(TOKEN, log_handler=None)
