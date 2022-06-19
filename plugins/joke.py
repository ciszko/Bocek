from bs4 import BeautifulSoup
from .log import get_logger
from discord.ext import commands
from .common import MyCog
from core.session import Session


log = get_logger(__name__)


class Joke(MyCog, name='joke'):
    def __init__(self, bot):
        self.bot = bot
        headers = {'User-Agent': 'Bocek/1.0'}
        url = 'https://perelki.net'
        self.session = Session(url, headers)

    @commands.command(name='żart', help='Losowy żarcik')
    async def random_joke(self, ctx):
        r = self.session.get('/random')
        dom = BeautifulSoup(r.content, 'html.parser')
        joke = dom.find('div', {'class': 'content'}).find(
            'div', {'class': 'container'}).get_text()
        msg = joke[:joke.find('Dowcip:')].replace(
            '\r', '').replace('\n', ' ').replace('\t', '')
        log.info(msg)
        if ctx.author.voice:
            tts = await self.bot.tts.create_tts(msg, 'pl')
            await self.bot.play_on_channel(tts)
        else:
            msg = (f'{ctx.author.name}, nie jesteś nawet na kanale...')
            await ctx.channel.send(msg)
        await ctx.message.delete()
