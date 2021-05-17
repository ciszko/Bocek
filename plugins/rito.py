import aiohttp
from random import choice
from .common import async_wrap

dictionary = {
    'deaths': ['%user% cioto', '%user% kiedy power spike?'],
    'kills': ['najs %user%', 'jedziesz %user%!', 'dawaj jeszcze jeden %user%'],
    'deaths_kills': ['zawsze coś %user%']
}


class Rito:
    def __init__(self):
        self.url_base = 'https://192.168.0.31:29999/liveclientdata/'
        self.connector = aiohttp.TCPConnector(ssl=False)
        self.to_look_for = ['kills', 'deaths', 'assists']
        self.players = ['Ciszkoo', 'LikeBanana',
                        'MEGACH0NKER', 'SwagettiYoloneze', 'Sabijak']
        self.stats = {}
        self.mode = 'idle'

    async def get_all_data(self):
        url = f'{self.url_base}allgamedata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url) as resp:
                return await resp.json()

    async def get_all_stats(self):
        url = f'{self.url_base}allgamedata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if data:
                    stats = []
                    for p in data['allPlayers']:
                        if p['summonerName'] not in self.players:
                            continue
                        scores = {
                            k: v for k, v in p['scores'].items() if k in self.to_look_for}
                        stats.append(
                            {'player': p['summonerName'], **scores})
                    self.stats = stats
                    return stats

    async def in_game(self):
        url = f'{self.url_base}allgamedata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            try:
                async with session.get(url, timeout=1) as resp:
                    x = await resp
                    if x:
                        return True
            except Exception as e:
                return e

    async def compare_stats(self):
        data1 = self.stats.copy()
        if not data1:
            await self.get_all_stats()
            return None
        data2 = await self.get_all_stats()
        to_ret = {}
        # print(data1, data2)
        for i, _ in enumerate(data1):
            set1 = set(data1[i].items())
            set2 = set(data2[i].items())
            if diff := set1 ^ set2:
                to_ret[data1[i]['player']] = set([x[0] for x in diff])
                if to_ret:
                    return self.create_msg(to_ret)
        return None

    def create_msg(self, stats):
        player, stat = choice(list(stats.items()))
        stat = '_'.join(list(stat))
        msg = choice(dictionary.get(stat))
        return msg.replace('%user%', player)
