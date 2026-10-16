from datetime import datetime, timedelta
from random import choice, randint
from typing import TYPE_CHECKING

from discord import CustomActivity, Game, Interaction, Streaming, app_commands
from discord.ext import tasks
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.glossary import Glossary
from utils.log import log
from utils.replies import defer, reply, reply_and_speak

if TYPE_CHECKING:
    from bot import MyBot


class RandomEvent(RhymeExtension, Cog, name="random_event"):
    def __init__(self, bot):
        self.bot: MyBot = bot
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
            return self.glossary.render(
                user=choice(members), all_users=", ".join(members)
            )
        return None

    @tasks.loop(seconds=8 * 60)
    async def random_check(self):
        self.update_join_time()
        if len(self.bot.voice_channel.members) <= 1:
            return
        if msg := self.random_say():
            await self.bot.speech.say(msg)

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
        if not await defer(interaction):
            return
        if not self.bot.is_caller_connected(interaction):
            await reply(interaction, "Nawet cię nie ma na kanale")
            return
        msg = self.random_say()
        if not msg:
            await reply(interaction, "Nie mam nic do powiedzenia")
            return
        await reply_and_speak(interaction, self.bot.speech, msg, voice="default")


async def setup(bot) -> None:
    await bot.add_cog(RandomEvent(bot))
