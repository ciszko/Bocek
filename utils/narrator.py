from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping

IGNORED_EVENTS = {"MinionsSpawning", "GameStart"}
MULTIKILLS = {2: "DoubleKill", 3: "TripleKill", 4: "QuadraKill", 5: "PentaKill"}


class Narrator:
    """Turns successive live-game event snapshots into a line to say, or None."""

    def __init__(
        self,
        glossary,
        players: Iterable[str],
        priorities: Mapping[str, float],
        roll: Callable[[], float] = random.random,
    ):
        self._glossary = glossary
        self._players = list(players)
        self._priorities = priorities
        self._roll = roll
        self._seen: int | None = None

    def reset(self) -> None:
        self._seen = None

    def narrate(self, snapshot: dict) -> str | None:
        events = snapshot.get("Events", [])
        if self._seen is None or len(events) < self._seen:
            self._seen = len(events)
            return None
        new, self._seen = events[self._seen :], len(events)
        classified = [c for event in new if (c := self._classify(event))]
        return self._pick(classified)

    def _classify(self, raw: dict) -> tuple[str, str] | None:
        """Returns (event name, player who it is about) for tracked players."""
        event = dict(raw)
        if not any(player in event.values() for player in self._players):
            return None
        name = event.get("EventName")
        if name in IGNORED_EVENTS:
            return None
        if "Acer" in event:
            event["KillerName"] = event["Acer"]
            name = "Ace"
        elif name == "FirstBlood":
            event["KillerName"] = event.get("Recipient")
        who = event.get("KillerName")
        if name == "Multikill":
            name = MULTIKILLS.get(int(event["KillStreak"]), name)
        elif name == "ChampionKill" and event.get("VictimName") in self._players:
            name, who = "ChampionDeath", event["VictimName"]
        elif name in ("DragonKill", "HeraldKill", "BaronKill") and (
            event.get("Stolen") == "True"
        ):
            name = name.replace("Kill", "Steal")
        if not who:
            return None
        return name, who

    def _pick(self, classified: list[tuple[str, str]]) -> str | None:
        for wanted, priority in self._priorities.items():
            who = next((w for name, w in classified if name == wanted), None)
            if who is not None and self._roll() < priority:
                voice, _ = self._glossary.get_value("player_transcript", who)
                return self._glossary.render(wanted, user=voice or who)
        return None
