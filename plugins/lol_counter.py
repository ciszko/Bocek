from bs4 import BeautifulSoup
import requests
from discord.ext import commands
from tabulate import tabulate
from difflib import get_close_matches
from functools import cached_property
from .common import async_wrap, MyCog
from .log import get_logger

log = get_logger(__name__)


class LolCounter(MyCog, name='lol_counter'):
    def __init__(self,  bot):
        self.bot = bot
        self.headers = {'User-Agent': 'Bocek/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @cached_property
    def champions(self):
        url = f'https://www.counterstats.net'
        for _ in range(3):
            try:
                r = self.session.get(url)
                break
            except ConnectionError:
                continue
        else:
            raise Exception('Kurcze jakiś problem z serwerem jest :(')

        dom = BeautifulSoup(r.content, 'html.parser')
        return [x['url'] for x in dom.find_all('div', {'class': 'champion-icon champList'})]

    def get_closest_champion(self, champion):
        if not (champ := next(iter(get_close_matches(champion, self.champions)), None)):
            raise Exception(f'Kurde, nie znam takiego czempiona jak {champion}')
        return champ

    @commands.command(name='counter', help='Zwraca x kontr na daną postać: $counter jinx x')
    async def counter(self, ctx, *arg):
        champion, counters = await self.get_lol_counters(*arg)
        response = f'**Kontry na {champion}:**\n```mma\n'
        response += self.print_tables_side_by_side(counters)
        response += '```'
        await ctx.send(response)
        await ctx.message.delete()

    @async_wrap
    def get_lol_counters(self, champion, limit=10):
        champion = self.get_closest_champion(champion)
        url = f'https://www.counterstats.net/league-of-legends/{champion}'
        for _ in range(3):
            try:
                r = self.session.get(url)
                break
            except ConnectionError:
                continue
        else:
            raise Exception('Kurcze jakiś problem z serwerem jest :(')

        dom = BeautifulSoup(r.content, 'html.parser')
        all_h3 = dom.find_all('h3')
        best_champion_dom = next(
            x for x in all_h3 if 'Best' in x.get_text()).parent
        worst_champion_dom = next(
            x for x in all_h3 if 'Worst' in x.get_text()).parent
        best_picks = best_champion_dom.find_all(
            'a', {'class': 'champ-box__row'})
        worst_picks = worst_champion_dom.find_all(
            'a', {'class': 'champ-box__row'})

        best = self.get_champs_percentage(best_picks)
        worst = self.get_champs_percentage(worst_picks)

        table1 = tabulate([['Champion', 'Punkty', '% win'], *best[:limit]],
                          headers="firstrow", tablefmt="github", floatfmt=".1f")
        table2 = tabulate([['Champion', 'Punkty', '% win'], *worst[:limit]],
                          headers="firstrow", tablefmt="github", floatfmt=".1f")

        return champion, [table1, table2]

    def get_champs_percentage(self, picks):
        out = []
        for pick in picks:
            del1 = 'vs-'
            l1 = len(del1)
            vs = pick['href'].find('vs-')
            del2 = pick['href'][vs + l1:].find('/') + vs + l1
            champion = (pick['href'][vs + l1:del2])
            points = pick.find('label').get_text()
            if not (win_ratio := pick.find('span', {'class': 'b'})):
                win_ratio = pick.find('span', {'class': 'w'})
            win_ratio = win_ratio.get_text()
            out.append([champion, points, win_ratio])
        return out

    def print_tables_side_by_side(self, tables, spacing=5):
        final = ''
        for i, table in enumerate(tables):
            tables[i] = table.split('\n')
        lenghts = [len(x) for x in tables]
        for i in range(max(lenghts)):
            for table in tables:
                if i <= len(table):
                    final += table[i].strip('\n')
                    final += spacing * ' '
            else:
                final += '\n'
        return final
