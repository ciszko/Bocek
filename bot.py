from __future__ import annotations

import asyncio
import os
from difflib import get_close_matches
from functools import cached_property

import discord
from discord.ext.commands import Bot

from utils.common import (
    BASE_DIR,
    GUILD,
    MP3_DIR,
    TOKEN,
    RhymeExtension,
)
from utils.glossary import Glossary
from utils.log import log
from utils.speech import Speech
from utils.speech_adapters import DiscordVoiceOutput, GoogleSynthesizer, make_fart
from utils.web import Web


class MyBot(Bot, RhymeExtension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ready = False
        self.glossary = Glossary(self, "talk.json")
        self.channel_list = []
        self.voice_channel_id = int(os.getenv("VOICE_CHANNEL_ID"))
        self.text_channel_id = int(os.getenv("TEXT_CHANNEL_ID"))
        self.speech: Speech | None = None
        self.web: Web | None = None
        os.makedirs(MP3_DIR, exist_ok=True)

    async def setup_hook(self):
        self.web = Web()
        self.speech = Speech(
            GoogleSynthesizer(), DiscordVoiceOutput(self), make_fart, MP3_DIR
        )
        await self.load_cogs()
        self.add_commands()

        guild = discord.Object(id=GUILD)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    @property
    def voice_channel(self):
        return next(
            (c for c in self.channel_list if c.id == self.voice_channel_id), None
        )

    @cached_property
    def text_channel(self):
        return next((c for c in self.channel_list if c.id == self.id), None)

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
            to_say = self.glossary.render("bocek_huju", user=message.author.name)

            if (
                hasattr(message.author.voice, "channel")
                and message.author.voice.channel
            ):
                await self.speech.say(to_say, voice="random")
            else:
                await message.add_reaction(self.get_emoji(283294977969356800))
                await message.reply(to_say)

        await self.process_commands(message)

    async def on_voice_state_update(self, member: discord.Member, before, after):
        if member == self.user or not self.ready:
            return
        if not hasattr(after, "channel") or not hasattr(after.channel, "name"):
            await self.speech.leave_if_empty()
            return
        if before.channel != after.channel and after.channel == self.voice_channel:
            to_say = self.glossary.render("greetings", user=member.global_name)
            await self.speech.say(to_say, voice="random", delay=0.75)
            return
        if after.channel != self.voice_channel:
            await self.speech.leave_if_empty()

    async def on_ready(self):
        self.channel_list = [c for c in self.get_all_channels()]
        self.ready = True
        self.speech.warm_up()
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

    async def close(self):
        log.info("Closing bot connections")
        if self.speech:
            await self.speech.shutdown()
        if self.web:
            await self.web.close()
        await super().close()

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
                await self.speech.say(response, voice="random")
            await interaction.followup.send(response)

        @self.tree.command(name="anus", description="anus anus nostradamus")
        async def anus(interaction: discord.Interaction):
            to_say = "anus anus nostradamus"
            await interaction.response.defer(ephemeral=True)
            if self.is_caller_connected(interaction):
                await self.speech.say(to_say, voice="random")
            await interaction.followup.send("anus")

        @self.tree.command(name="morda", description="zamyka mordę Bockowi")
        async def morda(interaction: discord.Interaction):
            await interaction.response.defer()
            if not self.is_caller_connected(interaction):
                return
            if self.speech.stop():
                await interaction.followup.send(
                    "już się zamykam <:siusiak:283294977969356800>"
                )

        @self.tree.command(name="pierd", description="puszcza bąka")
        async def pierd(interaction: discord.Interaction):
            await interaction.response.defer()
            if not self.is_caller_connected(interaction):
                return
            await self.speech.fart()
            await interaction.followup.send("😖💨")


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
