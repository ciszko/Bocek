import aiohttp


class Rito:
    def __init__(self):
        self.url_base = 'https://192.168.0.31:2999/liveclientdata/'
        self.connector = aiohttp.TCPConnector(ssl=False)
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
                    stats = [{'player': p['summonerName'], 'scores':p['scores']}
                             for p in data['allPlayers']]
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
            except aiohttp.ClientConnectionError:
                return False

    async def compare_stats(self):
        data1 = self.stats
        if not data1:
            return None
        data2 = await self.get_all_stats()
        to_ret = {}
        for i, _ in enumerate(data1):
            set1 = set(data1[i].items())
            set2 = set(data2[i].items())
            if diff := set1 ^ set2:
                to_ret[data1[i]['player']] = set([x[0] for x in diff])
                return to_ret

        return None
