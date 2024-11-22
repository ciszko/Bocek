from bs4 import BeautifulSoup
from discord import app_commands, Interaction, Embed, Color
from tabulate import tabulate
from difflib import get_close_matches
from functools import cached_property
from .common import async_wrap, MyCog
from .log import log
from core.session import Session
from typing import Dict, List


class LolCounter(MyCog, name="lol_counter"):
    def __init__(self, bot):
        self.bot = bot
        headers = {"User-Agent": "Bocek/1.0"}
        self.base_url = "https://www.counterstats.net"
        self.session = Session(self.base_url, headers)
        self.champions

    @cached_property
    def champions(self) -> Dict[str, str]:
        try:
            r = self.session.get("")
        except Exception:
            return {"": ""}

        dom = BeautifulSoup(r.content, "html.parser")
        champion_divs = dom.find_all("div", {"class": "champion-icon champList"})
        champs = {}
        for champion_div in champion_divs:
            url = champion_div["url"]
            name = champion_div.find("span", {"class": "name"}).get_text().strip()
            champs[name] = url
        champs = dict(sorted(champs.items()))
        return champs

    def get_closest_champion(self, champion) -> str:
        if not (
            champ := next(
                iter(get_close_matches(champion, self.champions.values())), None
            )
        ):
            raise Exception(f"Kurde, nie znam takiego czempiona jak {champion}")
        return champ

    async def champion_autocomplete(
        self,
        interaction: Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=champion, value=url)
            for champion, url in self.champions.items()
            if current.lower() in champion.lower()
        ][:20]

    @app_commands.command(
        name="counter", description="Zwraca kontry na daną postać: /counter jinx"
    )
    @app_commands.describe(champion="Postać na która zwrócone będą kontry")
    @app_commands.describe(limit="Limit liczby kontr")
    @app_commands.autocomplete(champion=champion_autocomplete)
    async def counter(self, interaction: Interaction, champion: str, limit: int = 10):
        log.info(f"{champion=}, {limit=}")
        await interaction.response.defer()
        champion, img, counters = await self.get_lol_counters(champion, limit)

        msg = f"```mma\n{counters}\n```"
        embed = Embed(
            title=f"**Kontry na {champion}:**",
            description=msg,
            color=Color.fuchsia(),
            url=f"{self.base_url}/league-of-legends/{champion}",
        )
        embed.set_thumbnail(url=img)
        await interaction.followup.send(embed=embed)

    @async_wrap
    def get_lol_counters(self, champion, limit=10):
        champion = self.get_closest_champion(champion)
        url = f"/league-of-legends/{champion}"
        try:
            r = self.session.get(url)
        except Exception:
            raise Exception("Kurcze jakiś problem z serwerem jest :(")

        dom = BeautifulSoup(r.content, "html.parser")

        img = dom.find("img", {"class": "icon"})["src"]
        all_h3 = dom.find_all("h3")
        best_champion_dom = next(x for x in all_h3 if "Best" in x.get_text()).parent
        worst_champion_dom = next(x for x in all_h3 if "Worst" in x.get_text()).parent
        best_picks = best_champion_dom.find_all("a", {"class": "champ-box__row"})
        worst_picks = worst_champion_dom.find_all("a", {"class": "champ-box__row"})

        best = self.get_champs_percentage(best_picks)[:limit]
        worst = self.get_champs_percentage(worst_picks)
        worst = list(reversed(worst[:limit]))

        table = tabulate(
            [["Champion", "% win"], *best, ["...", None], *worst],
            headers="firstrow",
            tablefmt="github",
            floatfmt=".1f",
            colalign=("left", "center", "center"),
        )

        return champion, img, table

    def get_champs_percentage(self, picks):
        out = []
        for pick in picks:
            champion = pick.find("span", {"class": "champion"}).get_text()
            if not (win_ratio := pick.find("span", {"class": "b"})):
                win_ratio = pick.find("span", {"class": "w"})
            win_ratio = win_ratio.get_text()
            out.append([champion, win_ratio])
        return out
