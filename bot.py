import asyncio
import os
from difflib import get_close_matches
from functools import cached_property
from time import time

import discord
from discord.ext.commands import Bot
from mutagen.mp3 import MP3

from utils.common import (
    BASE_DIR,
    FFMPEG,
    GUILD,
    MP3_DIR,
    TOKEN,
    RhymeExtension,
    replace_all,
)
from utils.glossary import Glossary
from utils.log import log


class MyBot(Bot, RhymeExtension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ready = False
        self.glossary = Glossary(self, "talk.json")
        self.channel_list = []
        self.voice_channel_id = int(os.getenv("VOICE_CHANNEL_ID"))
        self.text_channel_id = int(os.getenv("TEXT_CHANNEL_ID"))
        self.vc = None
        if not MP3_DIR.exists():
            os.makedirs(MP3_DIR)

    async def setup_hook(self):
        await self.load_cogs()
        self.add_commands()

        guild = discord.Object(id=GUILD)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    @cached_property
    def voice_channel(self):
        return next(
            (c for c in self.channel_list if c.id == self.voice_channel_id), None
        )

    @cached_property
    def text_channel(self):
        return next((c for c in self.channel_list if c.id == self.id), None)

    @property
    def tts(self):
        return self.get_cog("tts")

    async def load_cogs(self):
        for file in (BASE_DIR / "cogs").iterdir():
            if file.suffix != ".py" or file.stem == "__init__":
                continue
            try:
                await self.load_extension(f"cogs.{file.stem}")
                log.info(f"Loaded extension '{file.stem}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                log.error(f"Failed to load extension {file.stem}\n{exception}")

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
            user = member.name
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
        log.info("DISCONNECTING FROM VOICE")
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
                log.warning("Already connected to voice channel")
                await self.disconnect_from_voice()
                self.vc = await self.voice_channel.connect()
        if self.vc and self.vc.is_playing():
            log.warning("Already playing")
            return
        duration = MP3(message).info.length
        try:
            self.vc.play(
                discord.FFmpegOpusAudio(
                    executable=FFMPEG, source=message, options="-loglevel panic"
                )
            )
        except discord.errors.ClientException:
            log.error("Got disconnected from the channel")
            self.vc = await self.voice_channel.connect()
            self.vc.play(
                discord.FFmpegOpusAudio(
                    executable=FFMPEG, source=message, options="-loglevel panic"
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
        if isinstance(exception, discord.ext.commands.errors.CommandNotFound):
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
                    "Masz tak grube paluszki, że nie wiem o co chodzi :("
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
            to_say = "anus anus nostradamus"
            await interaction.response.defer(ephemeral=True)
            if (
                hasattr(interaction.user.voice, "channel")
                and interaction.user.voice.channel
            ):
                tts = await self.tts.create_tts(to_say, random=True)
                await self.play_on_channel(tts)
            await interaction.followup.send("anus")


if __name__ == "__main__":
    intents = discord.Intents.all()
    bot = MyBot(command_prefix="$", intents=intents)
    bot.run(TOKEN, log_handler=None)
