from datetime import timedelta, datetime
from discord import app_commands, Interaction
from discord.ext import commands
import asyncio
from .glossary import Glossary
from random import choice, randint
from .log import log
from .common import MyCog, replace_all

class RandomEvent(MyCog, name='random_event'):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.glossary = Glossary(self, 'random_join.json')
        self.join_at = None

    def random_say(self):
        if members := [
                x.name for x in self.bot.voice_channel.members if x.display_name != 'Bocek']:
            msg, placeholders = self.glossary.get_random()
            if 'user' in placeholders:
                user = choice(members)
            if 'all_users' in placeholders:
                all_users = ', '.join(members) if len(
                    members) > 1 else members[0]
            scope = locals()
            msg = replace_all(msg, {f'{{{p}}}': eval(p, scope) for p in placeholders})
            return msg
        return None

    async def random_check(self):
        await self.bot.wait_until_ready()
        while True:
            if not self.bot.ready:
                await asyncio.sleep(1)
                continue
            break

        while not self.bot.is_closed():
            if len(self.bot.voice_channel.members) > 1:
                if msg := self.random_say():
                    tts = await self.bot.tts.create_tts(msg, random=True)
                    await self.bot.play_on_channel(tts)

            wait_time = randint(8*60, 10*60)
            join_at = datetime.now() + timedelta(seconds=wait_time)
            self.join_at = join_at.strftime("%H:%M:%S")
            log.info(f'Random join on {self.join_at}')

            # TODO: fix activity
            # activ_no = choice([0, 1, 2, 3, 5])  # 4 is not supported :P
            # activ = Activity(
            #     type=activ_no,  name=self.glossary.get_random(f'activity_{activ_no}'))
            # await self.bot.change_presence(activity=activ)

            await asyncio.sleep(wait_time)

    @app_commands.command(name='kiedy', description='Informacja kiedy bocek coś se powie')
    async def when_join(self, interaction: Interaction):
        return await interaction.response.send_message(f'Będe z powrotem o {self.join_at}')

    @app_commands.command(name='powiedz', description='Coś se powiem')
    async def powiedz(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        msg = self.random_say()
        tts = await self.bot.tts.create_tts(msg, random=True)
        await self.bot.play_on_channel(tts)
        await interaction.followup.send(msg)
