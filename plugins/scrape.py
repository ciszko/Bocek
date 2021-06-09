from bs4 import BeautifulSoup
import requests
from discord.ext import commands
from tabulate import tabulate
from .common import async_wrap
from .log import get_logger

log = get_logger(__name__)


class LolCounter(commands.Cog, name='lol_counter'):
    def __init__(self,  bot):
        self.bot = bot
        self.headers = {'User-Agent': 'Bocek/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @commands.command(name='counter', help='Zwraca x kontr na daną postać: $counter jinx x')
    async def counter(self, ctx, *arg):
        counters = await self.get_lol_counters(*arg)
        response = f'**Kontry na {arg[0]}:**\n```'
        response += tabulate(
            [['Champion', '% win'], *counters], headers="firstrow", tablefmt="fancy_grid")
        response += '```'
        await ctx.send(response)
        await ctx.message.delete()

    @async_wrap
    def get_lol_counters(self, champion, limit=10):
        url = f'https://www.counterstats.net/league-of-legends/{champion}'
        r = self.session.get(url)
        dom = BeautifulSoup(r.content, 'html.parser')
        tight_dom = dom.find_all('div', {'class': 'champ-box__wrap new'})[0]
        picks = tight_dom.findAll('div', {'class': 'champ-box ALL'})
        best_picks, worst_picks, pop_counters = picks

        champs_perc = self.get_champs_and_percentage(best_picks)
        return champs_perc[:int(limit)]

    def get_champs_and_percentage(self, picks):
        to_ret = []
        champions = picks.findAll('a')
        for champ in champions:
            champ_name = champ['href'].split('/')[-3][3:]
            if perc := champ.find('span', {'class': 'percentage'}):
                percentage = perc.get_text()
            else:
                percentage = champ.find('span').find('b').get_text()
            to_ret.append([champ_name, percentage])
        return to_ret
