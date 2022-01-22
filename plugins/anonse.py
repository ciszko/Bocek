import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands
import requests
from unidecode import unidecode
from random import choice, randint
from .common import async_wrap
from .log import get_logger

log = get_logger(__name__)


class Anonse(commands.Cog, name='anonse'):
    def __init__(self, bot):
        self.bot = bot
        self.headers = {'User-Agent': 'Bocek/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.categories = {
            'ogolne': '1',
            'praca - szukam': '2',
            'seks': '3',
            'wakacje': '4',
            'szukam partnera': '5',
            'mieszkania': '6',
            'fetysze': '7',
            'komercyjne': '8',
            'szukam przyjaciela': '9',
            'szukam kobiety': '14',
            'korepetycje': '16',
            'praca - dam': '17',
            'widzialem cie': '18',
        }

    @commands.command(name='anonse', help='Zwraca losowe gejowe anonse')
    async def anonse(self, ctx, arg='fetysze'):
        # Gets voice channel of message author
        if ctx.author.voice:
            msg = await self.get_anonse(arg)
            tts = await self.bot.tts.create_tts(msg, 'pl')
            await self.bot.play_on_channel(tts)
            await self.bot.tts.delete_tts(msg)
        else:
            msg = (f'{ctx.author.name}, nie jesteś nawet na kanale...')
            await ctx.channel.send(msg)
            await ctx.message.delete()

    async def get_anonse(self, cat='fetysze'):
        cat = self.categories[unidecode(cat)]
        for i in range(1, 5):
            page = randint(1, int(30/i))
            anonse_list = await self.get_random_anonse(page, cat)
            if anonse_list:
                to_ret = choice(anonse_list)
                log.info(f'ANONSE: page={page}, cat={cat}, {to_ret}')
                return to_ret
        else:
            return 'Kurde belka, coś poszło nie tak'

    async def get_random_anonse(self, page, cat):
        url = f'https://anonse.inaczej.pl/?m=list&pg={page}&cat={cat}'
        for _ in range(3):
            try:
                r = self.session.get(url)
                break
            except Exception:
                await asyncio.sleep(0.5)
                continue
        dom = BeautifulSoup(r.content, 'html.parser')
        ads = dom.find_all('div', {'class': 'adcontent'})
        return [x.get_text().strip() for x in ads]
