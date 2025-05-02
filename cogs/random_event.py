import asyncio
from datetime import datetime, timedelta
from random import choice, randint

from discord import CustomActivity, Game, Interaction, Streaming, app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Cog

from utils.common import RhymeExtension, replace_all
from utils.glossary import Glossary
from utils.log import log


class RandomEvent(RhymeExtension, Cog, name="random_event"):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.glossary = Glossary(self, "random_join.json")
        self.tzinfo = datetime.now().astimezone().tzinfo
        self.join_at = None
        self.update_join_time()
        self.random_check.start()

    def update_join_time(self):
        new_interval = randint(8 * 60, 10 * 60)
        join_at = datetime.now(self.tzinfo) + timedelta(seconds=new_interval)
        self.join_at = join_at.strftime("%H:%M:%S")
        self.random_check.change_interval(seconds=new_interval)
        log.info(f"Next random join at {self.join_at}")

    def random_say(self):
        if members := [
            x.global_name for x in self.bot.voice_channel.members if not x.bot
        ]:
            msg, placeholders = self.glossary.get_random()
            if "user" in placeholders:
                user = choice(members)
            if "all_users" in placeholders:
                all_users = ", ".join(members) if len(members) > 1 else members[0]
            scope = locals()
            msg = replace_all(msg, {f"{{{p}}}": eval(p, scope) for p in placeholders})
            return msg
        return None

    @tasks.loop(seconds=8 * 60)
    async def random_check(self):
        self.update_join_time()
        if len(self.bot.voice_channel.members) <= 1:
            return
        if msg := self.random_say():
            tts = await self.bot.tts.create_tts(msg, random=True)
            await self.bot.play_on_channel(tts)

        choices = ("game", "streaming", "custom")
        type_ = choice(choices)
        match type_:
            case "game":
                name, _ = self.glossary.get_random("activity_game")
                activity = Game(name)
            case "streaming":
                name, _ = self.glossary.get_random("activity_game")
                activity = Streaming(name=name, url="https://anonse.inaczej.pl")
            case "custom":
                name, _ = self.glossary.get_random("activity_custom")
                activity = CustomActivity(name)
        await self.bot.change_presence(activity=activity)

    @random_check.before_loop
    async def random_check_before_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="kiedy", description="Informacja kiedy bocek coś se powie"
    )
    async def when_join(self, interaction: Interaction):
        return await interaction.response.send_message(
            f"Będe z powrotem o {self.join_at}"
        )

    @app_commands.command(name="powiedz", description="Coś se powiem")
    async def powiedz(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        msg = self.random_say()
        tts = await self.bot.tts.create_tts(msg, random=True)
        await self.bot.play_on_channel(tts)
        await interaction.followup.send(msg)


async def setup(bot) -> None:
    await bot.add_cog(RandomEvent(bot))
