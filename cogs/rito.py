from random import random
from typing import TYPE_CHECKING

from deepdiff import DeepDiff
from discord.ext import tasks
from discord.ext.commands import Cog

from utils.common import CONFIG, RhymeExtension, replace_all
from utils.glossary import Glossary
from utils.log import log
from utils.session import Session

if TYPE_CHECKING:
    from bot import MyBot

OFFLINE_WAIT = CONFIG["rito"]["offline-wait"]
ONLINE_WAIT = CONFIG["rito"]["online-wait"]
EVENT_PRIORITY = CONFIG["rito"]["event-possibility"]
PLAYERS = CONFIG["rito"]["players"]
LOL_GAME_IP = CONFIG["rito"]["lol-game-ip"]
LOL_GAME_PORT = CONFIG["rito"]["lol-game-port"]


class Rito(RhymeExtension, Cog, name="rito"):
    def __init__(self, bot):
        self.bot: MyBot = bot
        self.session = Session(
            f"https://{LOL_GAME_IP}:{LOL_GAME_PORT}/liveclientdata",
            retries=False,
        )
        self.glossary = Glossary(self, "rito.json")

        self.events: dict = {}
        self.rito_check.start()

    @tasks.loop(seconds=30)
    async def rito_check(self):
        if not await self.in_game():
            if self.rito_check.seconds != OFFLINE_WAIT:
                self.rito_check.change_interval(seconds=OFFLINE_WAIT)
            return
        if self.rito_check.seconds != ONLINE_WAIT:
            self.rito_check.change_interval(seconds=ONLINE_WAIT)
        if not (diff := await self.compare_stats()):
            return
        tts = await self.bot.tts.create_tts(diff)
        await self.bot.play_on_channel(tts)

    @rito_check.before_loop
    async def rito_check_before_loop(self):
        await self.bot.wait_until_ready()

    async def get_all_data(self):
        async with self.session.get("/allgamedata", verify=False) as resp:
            return await resp.json()

    async def get_all_events(self):
        async with self.session.get("/eventdata", verify=False) as resp:
            try:
                if data := await resp.json():
                    self.events = data
                    return data
            except Exception as e:
                log.exception(e)
                return None

    async def in_game(self):
        try:
            async with self.session as s:
                resp = await s.get("/eventdata", timeout=3, verify=False)
                if resp.status == 200:
                    log.info("In game detected")
                    return True
        except Exception as e:
            if "Timeout" not in str(e) or "Cannot connect to host" not in str(e):
                log.info(f"Not in game, {e.__class__.__name__}: {e}")
                return False
            log.exception(f"Unexpected error in in_game: {e}")
            return False

    async def compare_stats(self):
        """Returns the message if any"""
        events_prev = self.events.copy()
        if not events_prev:
            await self.get_all_events()
            return None
        events = await self.get_all_events()
        if not events:
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
            match int(event["KillStreak"]):
                case 2:
                    event["EventName"] = "DoubleKill"
                case 3:
                    event["EventName"] = "TripleKill"
                case 4:
                    event["EventName"] = "QuadraKill"
                case 5:
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
        return None


async def setup(bot) -> None:
    await bot.add_cog(Rito(bot))
