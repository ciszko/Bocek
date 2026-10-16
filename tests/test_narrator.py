import pytest

from utils.narrator import Narrator

PLAYERS = ["Ala", "Ola"]
PRIORITIES = {"PentaKill": 1, "TripleKill": 1, "ChampionKill": 0.3, "ChampionDeath": 0.3}


class FakeGlossary:
    transcripts = {"Ala": "ala-voice"}

    def get_value(self, section, key):
        assert section == "player_transcript"
        return self.transcripts.get(key), None

    def render(self, section, **context):
        return f"{section}:{context['user']}"


def snapshot(*events):
    return {"Events": list(events)}


def kill(killer, victim="Enemy", name="ChampionKill"):
    return {"EventName": name, "KillerName": killer, "VictimName": victim}


@pytest.fixture
def rolls():
    return {"value": 0.0}


@pytest.fixture
def narrator(rolls):
    return Narrator(
        FakeGlossary(), PLAYERS, PRIORITIES, roll=lambda: rolls["value"]
    )


def start(narrator, *initial):
    assert narrator.narrate(snapshot(*initial)) is None


def test_first_snapshot_only_sets_baseline(narrator):
    assert narrator.narrate(snapshot(kill("Ala"))) is None
    assert narrator.narrate(snapshot(kill("Ala"))) is None


def test_narrates_new_player_event(narrator):
    start(narrator)
    assert narrator.narrate(snapshot(kill("Ala"))) == "ChampionKill:ala-voice"


def test_events_are_narrated_once(narrator):
    start(narrator)
    snap = snapshot(kill("Ala"))
    narrator.narrate(snap)
    assert narrator.narrate(snap) is None


def test_ignores_events_not_involving_tracked_players(narrator):
    start(narrator)
    assert narrator.narrate(snapshot(kill("Stranger"))) is None


def test_ignores_game_start_events(narrator):
    start(narrator)
    event = {"EventName": "GameStart", "Who": "Ala", "KillerName": "Ala"}
    assert narrator.narrate(snapshot(event)) is None


def test_victim_player_becomes_champion_death(narrator):
    start(narrator)
    msg = narrator.narrate(snapshot(kill("Stranger", victim="Ola")))
    assert msg == "ChampionDeath:Ola"


def test_multikill_maps_streak_to_named_event(narrator):
    start(narrator)
    event = {"EventName": "Multikill", "KillerName": "Ala", "KillStreak": 5}
    assert narrator.narrate(snapshot(event)) == "PentaKill:ala-voice"


def test_ace_uses_acer_as_who(narrator):
    narrator = Narrator(FakeGlossary(), PLAYERS, {"Ace": 1}, roll=lambda: 0.0)
    start(narrator)
    event = {"EventName": "Ace", "Acer": "Ala", "KillerName": "Stranger"}
    assert narrator.narrate(snapshot(event)) == "Ace:ala-voice"


def test_first_blood_credits_recipient(narrator):
    narrator = Narrator(FakeGlossary(), PLAYERS, {"FirstBlood": 1}, roll=lambda: 0.0)
    start(narrator)
    event = {"EventName": "FirstBlood", "Recipient": "Ala", "KillerName": "Ala"}
    assert narrator.narrate(snapshot(event)) == "FirstBlood:ala-voice"


def test_stolen_objective_becomes_steal(narrator):
    narrator = Narrator(FakeGlossary(), PLAYERS, {"BaronSteal": 1}, roll=lambda: 0.0)
    start(narrator)
    event = {"EventName": "BaronKill", "KillerName": "Ala", "Stolen": "True"}
    assert narrator.narrate(snapshot(event)) == "BaronSteal:ala-voice"


def test_higher_priority_event_wins(narrator):
    start(narrator)
    triple = {"EventName": "Multikill", "KillerName": "Ala", "KillStreak": 3}
    msg = narrator.narrate(snapshot(kill("Ala"), triple))
    assert msg == "TripleKill:ala-voice"


def test_failed_roll_stays_silent(narrator, rolls):
    start(narrator)
    rolls["value"] = 0.9
    assert narrator.narrate(snapshot(kill("Ala"))) is None


def test_player_without_transcript_falls_back_to_game_name(narrator):
    start(narrator)
    assert narrator.narrate(snapshot(kill("Ola"))) == "ChampionKill:Ola"


def test_event_without_killer_is_skipped_not_fatal(narrator):
    start(narrator)
    broken = {"EventName": "GameEnd", "Result": "Win", "Who": "Ala"}
    assert narrator.narrate(snapshot(broken, kill("Ala"))) == "ChampionKill:ala-voice"


def test_new_game_starts_fresh_baseline(narrator):
    start(narrator, kill("Ala"), kill("Ala"))
    assert narrator.narrate(snapshot(kill("Ala"))) is None
    assert narrator.narrate(snapshot(kill("Ala"), kill("Ala"))) == "ChampionKill:ala-voice"


def test_reset_forgets_previous_game(narrator):
    start(narrator, kill("Ala"))
    narrator.reset()
    assert narrator.narrate(snapshot(kill("Ala"), kill("Ala"))) is None


def test_does_not_mutate_input_events(narrator):
    start(narrator)
    event = {"EventName": "Multikill", "KillerName": "Ala", "KillStreak": 2}
    narrator.narrate(snapshot(event))
    assert event == {"EventName": "Multikill", "KillerName": "Ala", "KillStreak": 2}
