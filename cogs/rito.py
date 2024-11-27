import asyncio
from random import random

import aiohttp
from deepdiff import DeepDiff
from discord.ext import tasks
from discord.ext.commands import Cog

from utils.common import RhymeExtension, replace_all
from utils.glossary import Glossary
from utils.log import log

OFFLINE_WAIT = 30
ONLINE_WAIT = 2
EVENT_PRIORITY = {
    "PentaKill": 1,
    "QuadraKill": 0.8,
    "TripleKill": 0.5,
    "BaronSteal": 1,
    "DragonSteal": 0.8,
    "DoubleKill": 0.4,
    "BaronKill": 0.5,
    "Ace": 0.5,
    "DragonKill": 0.3,
    "HeraldKill": 0.3,
    "FirstBlood": 0.5,
    "ChampionKill": 0.3,
    "ChampionDeath": 0.3,
    "InhibKilled": 0.3,
    "TurretKilled": 0.3,
}
PLAYERS = [
    "Ciszkoo",
    "LikeBanana",
    "Chonkey",
    "SwagettiYoloneze",
    "Sabijak",
    "Xubeks",
    "Nowik6300",
    "GodRevi",
    "Mαster Vi",
]


class Rito(RhymeExtension, Cog, name="rito"):
    def __init__(self, bot):
        self.bot = bot
        self.url_base = "https://192.168.0.31:29999/liveclientdata"
        self.connector = aiohttp.TCPConnector(ssl=False)
        self.glossary = Glossary(self, "rito.json")

        self.events = {}
        self.rito_check.start()

    @tasks.loop(seconds=30)
    async def rito_check(self):
        if not await self.in_game():
            if self.rito_check.seconds != OFFLINE_WAIT:
                self.rito_check.change_interval(OFFLINE_WAIT)
            return
        if self.rito_check.seconds != ONLINE_WAIT:
            self.rito_check.change_interval(ONLINE_WAIT)
        if not (diff := await self.compare_stats()):
            return
        tts = await self.bot.tts.create_tts(diff)
        await self.bot.play_on_channel(tts)

    @rito_check.before_loop
    async def rito_check_before_loop(self):
        await self.bot.wait_until_ready()

    async def get_all_data(self):
        url = f"{self.url_base}/allgamedata"
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        ) as session:
            async with session.get(url) as resp:
                return await resp.json()

    async def get_all_events(self):
        url = f"{self.url_base}/eventdata"
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        ) as session:
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
        url = f"{self.url_base}/eventdata"
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.get(url, timeout=3) as resp:
                    x = await resp.json()
                    if x:
                        return True
        except Exception as e:
            if "Timeout" not in str(e) or "Cannot connect to host" not in str(e):
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
            if not (
                diff := DeepDiff(events_prev, events).get("iterable_item_added", None)
            ):
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
        if not any(player in event.values() for player in PLAYERS):
            return
        if event["EventName"] in ["MinionsSpawning", "GameStart"]:
            return
        if "Acer" in event.keys():
            event["KillerName"] = event["Acer"]
            event["EventName"] = "Ace"
        elif event.get("EventName", None) == "FirstBlood":
            event["KillerName"] = event["Recipient"]
        event["Who"] = event["KillerName"]
        if event["EventName"] == "Multikill":
            if int(event["KillStreak"]) == 2:
                event["EventName"] = "DoubleKill"
            elif int(event["KillStreak"]) == 3:
                event["EventName"] = "TripleKill"
            elif int(event["KillStreak"]) == 4:
                event["EventName"] = "QuadraKill"
            elif int(event["KillStreak"]) == 5:
                event["EventName"] = "PentaKill"
        elif event["EventName"] == "ChampionKill" and event["VictimName"] in PLAYERS:
            event["EventName"] = "ChampionDeath"
            event["Who"] = event["VictimName"]
        elif (
            event["EventName"] in ["DragonKill", "HeraldKill", "BaronKill"]
            and event["Stolen"] == "True"
        ):
            event["EventName"] = event["EventName"].replace("Kill", "Steal")
        return event

    def create_msg(self, events):
        for event_name, prio in EVENT_PRIORITY.items():
            if event := next((e for e in events if e["EventName"] == event_name), None):
                if random() < prio:
                    player = event["Who"]
                    event_name = event["EventName"]
                    user, _ = self.glossary.get_value("player_transcript", player)
                    msg, msg_placeholders = self.glossary.get_random(event_name)
                    scope = locals()
                    msg = replace_all(
                        msg, {f"{{{p}}}": eval(p, scope) for p in msg_placeholders}
                    )
                    return msg
        else:
            return None


async def setup(bot) -> None:
    await bot.add_cog(Rito(bot))
