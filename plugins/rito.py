import aiohttp
from discord.ext import commands
from random import choice, random
import asyncio
from .glossary import Glossary
from .log import get_logger

log = get_logger(__name__)


class Rito(commands.Cog, name='rito'):
    def __init__(self, bot):
        self.bot = bot
        self.url_base = 'https://192.168.0.31:29999/liveclientdata/'
        self.connector = aiohttp.TCPConnector(ssl=False)
        self.to_look_for = ['kills', 'deaths', 'assists']
        self.players = ['Ciszkoo', 'LikeBanana',
                        'MEGACH0NKER', 'SwagettiYoloneze', 'Sabijak']
        self.glossary = Glossary(self, 'rito.json')

        self.stats = {}
        self.mode = 'idle'

    async def rito_check(self):
        await self.bot.wait_until_ready()
        wait_time = 30
        while not self.bot.is_closed():
            if in_game := await self.in_game():
                wait_time = 10
                diff = await self.compare_stats()
                if diff and random() < 0.3:
                    tts = await self.bot.tts.create_tts(diff, 'pl')
                    await self.bot.play_on_channel(self.bot.voice_channel, tts)
            else:
                wait_time = 30
            await asyncio.sleep(wait_time)

    async def get_all_data(self):
        url = f'{self.url_base}allgamedata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url) as resp:
                return await resp.json()

    async def get_all_stats(self):
        url = f'{self.url_base}allgamedata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url) as resp:
                try:
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
                except Exception as e:
                    log.info(e)
                    return None

    async def in_game(self):
        url = f'{self.url_base}allgamedata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            try:
                async with session.get(url, timeout=1) as resp:
                    x = await resp.json()
                    if x:
                        return True
            except Exception as e:
                if str(e) != '' and 'Timeout' not in str(e):
                    log.info(e)
                return False

    async def compare_stats(self):
        data1 = self.stats.copy()
        if not data1:
            await self.get_all_stats()
            return None
        if data2 := await self.get_all_stats():
            ...
        else:
            return None
        to_ret = {}
        # log.info(data1, data2)
        try:
            for i, _ in enumerate(data1):
                set1 = set(data1[i].items())
                set2 = set(data2[i].items())
                if diff := set1 ^ set2:
                    to_ret[data1[i]['player']] = set([x[0] for x in diff])
                    if to_ret:
                        return self.create_msg(to_ret)
        except Exception as e:
            log.info(e)
        return None

    def create_msg(self, stats):
        player, stat = choice(list(stats.items()))
        stat = '_'.join(list(stat))
        player = self.glossary.get_value('player_transcript', player)
        if msg := self.glossary.get_random(stat, user=player):
            return msg
        return None
