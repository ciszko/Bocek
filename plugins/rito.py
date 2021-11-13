import aiohttp
from deepdiff import DeepDiff
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
        self.players = ['Ciszkoo', 'LikeBanana',
                        'MEGACH0NKER', 'SwagettiYoloneze', 'Sabijak', 'Xubeks']
        self.glossary = Glossary(self, 'rito.json')

        self.events = {}
        self.mode = 'idle'
        self.event_priority = [
            'PentaKill',
            'QuadraKill',
            'TripleKill',
            'BaronSteal',
            'DragonSteal',
            'DoubleKill',
            'BaronKill',
            'Ace',
            'DragonKill',
            'HeraldKill',
            'FirstBlood',
            'ChampionKill',
            'ChampionDeath',
            'InhibKilled',
            'TurretKilled',
        ]

    async def rito_check(self):
        await self.bot.wait_until_ready()
        wait_time = 30
        while not self.bot.is_closed():
            if in_game := await self.in_game():
                wait_time = 5
                diff = await self.compare_stats()
                if diff and random() < 1:
                    tts = await self.bot.tts.create_tts(diff, 'pl')
                    await self.bot.play_on_channel(tts)
            else:
                wait_time = 30
            await asyncio.sleep(wait_time)

    async def get_all_data(self):
        url = f'{self.url_base}allgamedata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url) as resp:
                return await resp.json()

    async def get_all_events(self):
        url = f'{self.url_base}eventdata'
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url) as resp:
                try:
                    data = await resp.json()
                    if data:
                        self.events = data
                        return data
                except Exception as e:
                    log.exception(e)
                    return None

    async def in_game(self):
        url = f'{self.url_base}eventdata'
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.get(url, timeout=3) as resp:
                    x = await resp.json()
                    if x:
                        return True
        except Exception as e:
            if 'Timeout' not in str(e) or 'Cannot connect to host' not in str(e):
                ...
            return False

    async def compare_stats(self):
        """Returns the message if any"""
        events_prev = self.events.copy()
        if not events_prev:
            await self.get_all_events()
            return None
        if events := await self.get_all_events():
            ...
        else:
            return None
        to_ret = []
        try:
            if not (diff := DeepDiff(events_prev, events).get('iterable_item_added', None)):
                return None
            for event in diff.values():
                if not (processed := self.handle_event(event)):
                    continue
                to_ret.append(processed)
            if to_ret:
                return self.create_msg(to_ret)
        except Exception as e:
            log.exception(e)
        return None

    def handle_event(self, event):
        if not any(player in event.values() for player in self.players):
            return
        if event['EventName'] in ['MinionsSpawning', 'GameStart']:
            return
        if 'Acer' in event.keys():
            event['KillerName'] = event['Acer']
            event['EventName'] = 'Ace'
        elif event.get('EventName', None) == 'FirstBlood':
            event['KillerName'] = event['Recipient']
        event['Who'] = event['KillerName']
        if event['EventName'] == 'Multikill':
            if int(event['KillStreak']) == 2:
                event['EventName'] = 'DoubleKill'
            elif int(event['KillStreak']) == 3:
                event['EventName'] = 'TripleKill'
            elif int(event['KillStreak']) == 4:
                event['EventName'] = 'QuadraKill'
            elif int(event['KillStreak']) == 5:
                event['EventName'] = 'PentaKill'
        elif event['EventName'] == 'ChampionKill' and event['VictimName'] in self.players:
            event['EventName'] = 'ChampionDeath'
            event['Who'] = event['VictimName']
        elif event['EventName'] in ['DragonKill', 'HeraldKill', 'BaronKill'] and event['Stolen'] == 'True':
            event['EventName'] = event['EventName'].replace('Kill', 'Steal')
        return event

    def create_msg(self, events):
        if not (event := next(
                (event for event in events if event['EventName'] in self.event_priority), None)):
            return None
        player = event['Who']
        event_name = event['EventName']
        player = self.glossary.get_value('player_transcript', player)
        if msg := self.glossary.get_random(event_name, user=player):
            return msg
        return None
