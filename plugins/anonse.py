import re
import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands
from unidecode import unidecode
from random import choice, randint

from .common import MyCog
from .log import get_logger
from core.session import Session

log = get_logger(__name__)


class Anonse(MyCog, name='anonse'):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = 'https://anonse.inaczej.pl'
        headers = {'User-Agent': 'Bocek/1.0'}
        self.session = Session(self.base_url, headers)
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

    @commands.command(name='anonse', help='Zwraca losowe gejowe anonse z wybranej kategorii. Default: $anonse "fetysze"')
    async def anonse(self, ctx, arg='fetysze'):
        # Gets voice channel of message author
        if ctx.author.voice:
            author, msg, img = await self.get_anonse(arg)
            n = '\n'
            await ctx.message.reply(f'**{author}**{msg}{n + img if img else ""}')
            tts = await self.bot.tts.create_tts(msg, 'pl')
            await self.bot.play_on_channel(tts)
        else:
            msg = (f'{ctx.author.name}, nie jesteś nawet na kanale...')
            await ctx.message.reply(msg)

    @commands.command(name='kategorie', help='Zwraca możliwe kategorie')
    async def kategorie(self, ctx):
        categories = '```' + '\n'.join(f'"{c}"' for c in self.categories.keys()) + '```'
        await ctx.message.reply(categories)

    async def get_anonse(self, cat='fetysze'):
        cat = self.categories[unidecode(cat)]
        for i in range(1, 5):
            page = randint(1, int(30/i))
            anonse_list = await self.get_anonses(page, cat)
            if anonse_list:
                anonse_item = choice(anonse_list)
                anonse_image = anonse_item.find('a', {'class': 'fancybox'})
                anonse_image = f'{self.base_url}/' + anonse_image['href'] if anonse_image else None
                anonse_text = anonse_item.find('div', {'class': 'adcontent'}).get_text().strip()
                anonse_author = anonse_item.find('i', {'class': 'icon-user'}).next_sibling
                log.info(f'ANONSE: page={page}, cat={cat}, {anonse_text}')
                return anonse_author, anonse_text, anonse_image
        else:
            return 'Kurde belka, coś poszło nie tak'

    async def get_anonses(self, page, cat):
        url = f'/?m=list&pg={page}&cat={cat}'
        for _ in range(3):
            try:
                r = self.session.get(url)
                break
            except Exception:
                await asyncio.sleep(0.5)
                continue
        dom = BeautifulSoup(r.content, 'html.parser')
        return dom.find_all('div', {'class': 'listaditem'})

    def replace_numbers(self, msg):
        pattern = r'(\d+)[\/,l ]*(\d+)[\/,l ]*(\d+)[\/,l ]?(\d+)?'
        groups = [int(x) for x in re.search(pattern, msg).groups() if x]
        groups = sorted(groups, reverse=True)
        if len(groups) == 3:
            return f'{groups[0]}cm, {groups[1]}lat, siurdol {groups[2]}cm'
        return f'{groups[0]}cm, {groups[1]}kg, {groups[2]}lat, siurdol {groups[3]}cm'
