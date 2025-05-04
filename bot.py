from __future__ import annotations

import asyncio
import os
from difflib import get_close_matches
from functools import cached_property
from time import time
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Bot

from utils.common import (
    BASE_DIR,
    FFMPEG,
    FFPMEG_OPTIONS,
    GUILD,
    MP3_DIR,
    TOKEN,
    RhymeExtension,
    replace_all,
)
from utils.glossary import Glossary
from utils.log import log

if TYPE_CHECKING:
    from cogs.tts import Tts


class MyBot(Bot, RhymeExtension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ready = False
        self.glossary = Glossary(self, "talk.json")
        self.channel_list = []
        self.voice_channel_id = int(os.getenv("VOICE_CHANNEL_ID"))
        self.text_channel_id = int(os.getenv("TEXT_CHANNEL_ID"))
        self.vc = None
        self.is_connecting = False
        os.makedirs(MP3_DIR, exist_ok=True)

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
    def tts(self) -> Tts:
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

            tts = await self.tts.create_tts(to_say, random=True)
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
        if not hasattr(after, "channel") or not hasattr(after.channel, "name"):
            if len([m for m in self.voice_channel.members if not m.bot]) < 1:
                await self.disconnect_from_voice()
                await self.tts.delete_all_tts()
            return
        if before.channel != after.channel and after.channel == self.voice_channel:
            await asyncio.sleep(0.75)
            to_say, placeholders = self.glossary.get_random("greetings")
            user = member.global_name
            scope = locals()
            to_say = replace_all(
                to_say, {f"{{{p}}}": eval(p, scope) for p in placeholders}
            )
            start_time = time()
            tts = await self.tts.create_tts(to_say, random=True)
            log.info(f"TTS generation took {time() - start_time:.2f}s")
            start_time = time()
            await self.play_on_channel(tts)
            log.info(f"Playback took {time() - start_time:.2f}s")
            return
        if (
            after.channel != self.voice_channel
            and len([m for m in self.voice_channel.members if not m.bot]) < 1
            and self.vc
        ):
            await self.disconnect_from_voice()
            await self.tts.delete_all_tts()

    async def disconnect_from_voice(self):
        log.info("DISCONNECTING FROM VOICE")
        for vc in self.voice_clients:
            await vc.disconnect(force=True)
        self.vc = None

    async def play_on_channel(self, message=None):
        if not self.ready:
            log.info("Bot not ready, skipping playback")
            return
        if message is None:
            return
        non_bot_members = len([m for m in self.voice_channel.members if not m.bot])
        log.info(f"Non-bot members in voice channel: {non_bot_members}")
        if non_bot_members < 1:
            if self.vc:
                await self.disconnect_from_voice()
            return
        if self.is_connecting:
            log.warning("Already attempting to connect to voice channel")
            return
        if not self.vc or not self.vc.is_connected():
            try:
                self.is_connecting = True
                log.info("Connecting to voice channel")
                start_time = time()
                self.vc = await asyncio.wait_for(
                    self.voice_channel.connect(), timeout=6
                )
                log.info(f"Voice connection took {time() - start_time:.2f}s")
            except asyncio.TimeoutError:
                log.error("Voice connection timed out")
                return
            except discord.ClientException as e:
                log.warning(f"Voice connection error: {e}")
                await self.disconnect_from_voice()
                try:
                    self.vc = await asyncio.wait_for(
                        self.voice_channel.connect(), timeout=6
                    )
                    log.info(f"Reconnection took {time() - start_time:.2f}s")
                except Exception as e:
                    log.error(f"Failed to reconnect: {e}")
                    return
            finally:
                self.is_connecting = False
        if self.vc and self.vc.is_playing():
            log.warning("Already playing")
            return

        def after_playback(error):
            if error:
                log.error(f"Playback error: {error}")
            loop = self.loop
            loop.create_task(self.tts.delete_tts(message))
            if len([m for m in self.voice_channel.members if not m.bot]) < 1:
                loop.create_task(self.disconnect_from_voice())

        try:
            log.info(f"Playing audio: {message}")
            start_time = time()
            source = discord.FFmpegOpusAudio(
                executable=FFMPEG,
                source=message,
                options=FFPMEG_OPTIONS,
            )
            self.vc.play(source, after=after_playback)
            log.info(f"Audio playback started in {time() - start_time:.2f}s")
        except discord.errors.ClientException as e:
            log.error(f"Failed to play audio: {e}")

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

    def is_caller_connected(self, interaction: discord.Interaction) -> bool:
        if hasattr(interaction.user, "voice") and hasattr(
            interaction.user.voice, "channel"
        ):
            return True
        return False

    async def handle_defering(self, interaction: discord.Interaction):
        failed_to_defer = False
        try:
            await interaction.response.defer()
        except discord.errors.NotFound as e:
            log.error(f"Failed to defer interaction: {e}")
            failed_to_defer = True
        if failed_to_defer:
            try:
                await asyncio.sleep(1)
                await interaction.response.defer()
            except discord.errors.HTTPException:
                return
            except Exception as e:
                log.exception(e)

    def add_commands(self):
        @self.tree.command(name="siusiak", description="powie prawde o siusiaku")
        async def siusiak(interaction: discord.Interaction):
            """/siusiak"""
            siusiak, _ = self.glossary.get_random("siusiak")
            response = f"{interaction.user.name} ma {siusiak} siusiaka"
            await interaction.response.defer()
            if self.is_caller_connected(interaction):
                tts = await self.tts.create_tts(response, random=True)
                await self.play_on_channel(tts)
            await interaction.followup.send(response)

        @self.tree.command(name="anus", description="anus anus nostradamus")
        async def anus(interaction: discord.Interaction):
            to_say = "anus anus nostradamus"
            await interaction.response.defer(ephemeral=True)
            if self.is_caller_connected(interaction):
                tts = await self.tts.create_tts(to_say, random=True)
                await self.play_on_channel(tts)
            await interaction.followup.send("anus")


async def close(self):
    log.info("Closing bot connections")
    await self.disconnect_from_voice()
    await super().close()


if __name__ == "__main__":
    intents = discord.Intents.all()
    bot = MyBot(command_prefix="$", intents=intents)
    try:
        bot.run(TOKEN, log_handler=None)
    except Exception as e:
        log.warning("Bot stopped unhandled exception")
        log.exception(e)
        bot.loop.run_until_complete(bot.close())
        exit(0)
