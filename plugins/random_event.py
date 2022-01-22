from datetime import timedelta, datetime
from discord.ext import commands
from discord import Activity
import asyncio
from .glossary import Glossary
from random import choice, randint
from .log import get_logger

log = get_logger(__name__)


class RandomEvent(commands.Cog, name='random_event'):
    def __init__(self, bot):
        self.bot = bot
        self.glossary = Glossary(self, 'random_join.json')
        self.join_at = None

    async def random_check(self):
        await self.bot.wait_until_ready()
        while True:
            if not self.bot.ready:
                await asyncio.sleep(1)
                continue
            break

        while not self.bot.is_closed():
            if len(self.bot.voice_channel.members) >= 1:
                # if len(x.members) > 0:
                #     self.poll_task = self.loop.create_task(
                #         self.random_poll(len(x.members)))
                if members := [
                        x.display_name for x in self.bot.voice_channel.members if x.display_name != 'Bocek']:
                    user = choice(members)
                    all_users = ', '.join(members) if len(
                        members) > 1 else members[0]
                    msg = self.glossary.get_random(
                        user=user, all_users=all_users)
                    tts = await self.bot.tts.create_tts(msg, 'pl', random=True)
                    await self.bot.play_on_channel(tts)
                    await self.bot.tts.delete_tts(msg)

            wait_time = randint(8*60, 10*60)
            join_at = datetime.now() + timedelta(seconds=wait_time)
            self.join_at = join_at.strftime("%H:%M:%S")
            log.info(f'Random join on {self.join_at}')

            activ_no = choice([0, 1, 2, 3, 5])  # 4 is not supported :P
            activ = Activity(
                type=activ_no,  name=self.glossary.get_random(f'activity_{activ_no}'))
            await self.bot.change_presence(activity=activ)

            await asyncio.sleep(wait_time)

    @commands.command(name='kiedy', help='Informacja kiedy bot znowu zrobi random join')
    async def when_join(self, ctx, *args):
        return await ctx.message.reply(f'Będe z powrotem o {self.join_at}')

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
        self.poll_msg = await self.bot.text_channel.send(to_send)

        await asyncio.sleep(poll_end)

        scores = {k: get_likes(v) for k, v in self.poll_msgs.items()}
        best_author = max(scores, key=lambda x: scores[x])

        log.info(
            f'Poll has ended, best msg: {self.poll_msgs[best_author].content}')
        self.bot.text_channel.send(
            f'Ankieta zakończona. Wygrał {best_author}')
        # reset poll variables
        self.poll_msgs = {}
        self.poll_msg = None
        return

    @commands.Cog.listener()
    async def on_message(self, message):
        return
        msg = message.content.lower()
        if hasattr(self.poll_msg) and hasattr(msg, 'reference') and msg.reference.message_id == self.poll_msg.id:
            self.poll_msgs[msg.author] = msg
