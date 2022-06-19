from bs4 import BeautifulSoup
from .log import get_logger
from discord.ext import commands
from .common import MyCog
from core.session import Session


log = get_logger(__name__)


class Slang(MyCog, name='slang'):
    def __init__(self, bot):
        self.bot = bot
        headers = {'User-Agent': 'Bocek/1.0'}
        url = 'https://www.miejski.pl'
        self.session = Session(url, headers)

    @commands.command(name='slang', help='Losowy miejski.pl')
    async def random_joke(self, ctx):
        r = self.session.get('/losuj')
        dom = BeautifulSoup(r.content, 'html.parser')
        article = dom.find('article')
        word = article.find('h1').text
        desc = article.find('p').text.replace('\r\n', '').strip()
        msg = f'{word} - {desc}'
        log.info(msg)
        if ctx.author.voice:
            tts = await self.bot.tts.create_tts(msg, 'pl')
            await ctx.channel.send(msg)
            await self.bot.play_on_channel(tts)
        else:
            msg = (f'{ctx.author.name}, nie jesteś nawet na kanale...')
            await ctx.channel.send(msg)
        await ctx.message.delete()
