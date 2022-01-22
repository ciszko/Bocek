import requests
from bs4 import BeautifulSoup
from .log import get_logger
from discord.ext import commands


log = get_logger(__name__)


class Joke(commands.Cog, name='jokes'):
    def __init__(self, bot):
        self.bot = bot
        self.headers = {'User-Agent': 'Bocek/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self.url = 'https://perelki.net/random'

    @commands.command(name='żart', help='Losowy żarcik')
    async def random_joke(self, ctx):
        r = self.session.get(self.url)
        dom = BeautifulSoup(r.content, 'html.parser')
        joke = dom.find('div', {'class': 'content'}).find(
            'div', {'class': 'container'}).get_text()
        msg = joke[:joke.find('Dowcip:')].replace(
            '\r', '').replace('\n', ' ').replace('\t', '')
        log.info(msg)
        if ctx.author.voice:
            tts = await self.bot.tts.create_tts(msg, 'pl')
            await self.bot.play_on_channel(tts)
            await self.bot.tts.delete_tts(msg)
        else:
            msg = (f'{ctx.author.name}, nie jesteś nawet na kanale...')
            await ctx.channel.send(msg)
        await ctx.message.delete()
