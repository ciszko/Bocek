from __future__ import annotations

import asyncio
import io
import re
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from random import choice, shuffle
from typing import TYPE_CHECKING, Awaitable, Callable, Iterable, List, Optional, TypeVar
from urllib.parse import urlsplit

import discord
from bs4 import BeautifulSoup
from discord import Interaction, app_commands
from discord.app_commands import Choice
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log

if TYPE_CHECKING:
    from bot import MyBot

BASE_URL = "https://anonse.inaczej.pl"
PAGE_CONCURRENCY = 3
PAGE_ATTEMPTS = 5
MAX_PAGE_TTL = 3600
DEFAULT_MAX_PAGE = 30

T = TypeVar("T")


def list_url(page: int, cat: str, region: str) -> str:
    url = f"{BASE_URL}/?m=list&pg={page}&cat={cat}"
    if region != "0":
        url += f"&region={region}"
    return url


async def first_usable(
    fetch: Callable[[int], Awaitable[Optional[T]]],
    pages: Iterable[int],
    concurrency: int = PAGE_CONCURRENCY,
) -> Optional[T]:
    """Run fetch over pages, at most `concurrency` at once.

    Returns the first non-None result and cancels the rest; None if none qualify.
    """
    remaining = iter(pages)
    pending: set[asyncio.Task] = set()
    try:
        while True:
            while len(pending) < concurrency and (page := next(remaining, None)):
                pending.add(asyncio.ensure_future(fetch(page)))
            if not pending:
                return None
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                if (result := task.result()) is not None:
                    return result
    finally:
        for task in pending:
            task.cancel()


CategoryChoices = [
    Choice(name="ogolne", value="1"),
    Choice(name="praca - szukam", value="2"),
    Choice(name="seks", value="3"),
    Choice(name="wakacje", value="4"),
    Choice(name="szukam partnera", value="5"),
    Choice(name="mieszkania", value="6"),
    Choice(name="fetysze", value="7"),
    Choice(name="komercyjne", value="8"),
    Choice(name="szukam przyjaciela", value="9"),
    Choice(name="szukam kobiety", value="14"),
    Choice(name="korepetycje", value="16"),
    Choice(name="praca - dam", value="17"),
    Choice(name="widzialem cie", value="18"),
]

RegionChoices = [
    Choice(name="wszystko", value="0"),
    Choice(name="dolnoslaskie", value="1"),
    Choice(name="kujawsko - pomorskie", value="2"),
    Choice(name="lubelskie", value="3"),
    Choice(name="lubuskie", value="4"),
    Choice(name="łódzkie", value="5"),
    Choice(name="małopolskie", value="6"),
    Choice(name="mazowieckie", value="7"),
    Choice(name="opolskie", value="8"),
    Choice(name="podkarpackie", value="9"),
    Choice(name="podlaskie", value="10"),
    Choice(name="pomorskie", value="11"),
    Choice(name="śląskie", value="12"),
    Choice(name="świętokrzyskie", value="13"),
    Choice(name="warmińsko-mazurskie", value="14"),
    Choice(name="wielkopolskie", value="15"),
    Choice(name="zachodniopomorskie", value="16"),
    Choice(name="cała Polska", value="17"),
    Choice(name="zagranica", value="18"),
]

SiurdolChoices = [Choice(name="tak", value="tak"), Choice(name="może", value="może")]


@dataclass
class AnonseAd:
    author: str
    text: str
    image: Optional[str]
    location: str
    date: datetime
    age: Optional[str]
    footer: str = field(init=False)

    def __post_init__(self):
        self.footer = "\n".join((x for x in [self.age, self.location] if x))

    @classmethod
    def from_html(cls, html) -> AnonseAd:
        image = html.find("a", {"class": "fancybox"})
        image = "/".join((BASE_URL, image["href"])) if image else None
        text = html.find("div", {"class": "adcontent"}).get_text().strip()
        author = html.find("i", {"class": "icon-user"}).next_sibling.strip()
        location = html.find("i", {"class": "icon-location-arrow"}).next_sibling
        raw_date = html.find("i", {"class": "icon-calendar"}).next_sibling
        age = html.find("i", {"class": "icon-leaf"})
        age = age.next_sibling if age else ""

        try:
            if raw_date.startswith("Dzisiaj"):
                time_str = raw_date.split(" ")[1]
                today = datetime.now()
                date = datetime.strptime(
                    f"{today.strftime('%d-%m-%Y')} {time_str}", "%d-%m-%Y %H:%M"
                )
            elif raw_date.startswith("Wczoraj"):
                time_str = raw_date.split(" ")[1]
                yesterday = datetime.now() - timedelta(days=1)
                date = datetime.strptime(
                    f"{yesterday.strftime('%d-%m-%Y')} {time_str}", "%d-%m-%Y %H:%M"
                )
            else:
                date = datetime.strptime(raw_date, "%d-%m-%Y %H:%M")
        except (IndexError, ValueError):
            date = datetime.now()

        return cls(
            author=author,
            text=text,
            image=image,
            location=location,
            date=date,
            age=age,
        )


class Anonse(RhymeExtension, Cog, name="anonse"):
    name = "anonse"

    def __init__(self, bot):
        self.bot: MyBot = bot
        self._max_pages: dict[tuple[str, str], tuple[float, int]] = {}

    class DeleteImageButton(discord.ui.View):
        def __init__(self, *, msg=None, img=None, embed=None):
            self.msg = msg
            self.img = img
            self.embed = embed
            super().__init__()

        @discord.ui.button(
            label="Usuń siurdolka",
            style=discord.ButtonStyle.red,
            emoji="<:siusiak:283294977969356800>",
        )
        async def on_click(self, interaction: Interaction, button: discord.ui.Button):
            button.disabled = True
            button.label = "Siurdolek usunięty"
            self.add_item(
                discord.ui.Button(
                    label="Zobacz siurdolka",
                    url=self.img,
                    style=discord.ButtonStyle.green,
                    emoji="<:siusiak:283294977969356800>",
                )
            )
            self.embed.set_image(url=None)
            await interaction.message.edit(embed=self.embed, view=self, attachments=[])
            await interaction.response.defer()

    @app_commands.command(
        name="anonse",
        description='Zwraca losowe gejowe anonse z wybranej kategorii. Default: /anonse "fetysze"',
    )
    @app_commands.describe(kategoria="Kategoria z której szukać anonsa")
    @app_commands.describe(region="Region z którego szukać anonsa")
    @app_commands.describe(siurdol="Wymusza siurdola")
    @app_commands.choices(kategoria=CategoryChoices)
    @app_commands.choices(region=RegionChoices)
    @app_commands.choices(siurdol=SiurdolChoices)
    async def anonse(
        self,
        interaction: Interaction,
        kategoria: app_commands.Choice[str] = "7",
        region: app_commands.Choice[str] = "0",
        siurdol: Optional[str] = "może",
    ):
        await self.bot.handle_defering(interaction)
        if not self.bot.is_caller_connected(interaction):
            try:
                await interaction.followup.send(
                    f"{interaction.user.name}, nie jesteś nawet na kanale..."
                )
            except discord.errors.NotFound as e:
                log.error(f"Failed to send followup: {e}")
            return

        try:
            kategoria = kategoria if isinstance(kategoria, str) else kategoria.value
            region = region if isinstance(region, str) else region.value
            log.info(f"{kategoria=}, {region=}")
            anonse = await self.get_anonse(kategoria, region, siurdol)
            if not anonse:
                try:
                    await interaction.followup.send(
                        "Coś nie mogę znaleźć anonsa :disappointed_relieved:"
                    )
                except discord.errors.NotFound as e:
                    log.error(f"Failed to send followup: {e}")
                return

            cat = next(c.name for c in CategoryChoices if c.value == kategoria)
            reg = next(r.name for r in RegionChoices if r.value == region)

            title = f"Kategoria: *{cat}*, region: *{reg}*"
            embed = discord.Embed(
                title=title, description=anonse.text, color=discord.Color.fuchsia()
            )
            embed.set_author(name=anonse.author)
            log.info(f"Anonse image: {anonse.image}")
            embed.set_footer(text=anonse.footer)
            embed.timestamp = anonse.date

            view = (
                Anonse.DeleteImageButton(
                    msg=anonse.text, img=anonse.image, embed=deepcopy(embed)
                )
                if anonse.image
                else discord.utils.MISSING
            )

            if anonse.image:
                image_data = await self.bot.web.read(anonse.image)
                suffix = Path(urlsplit(anonse.image).path).suffix.lower()
                if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                    suffix = ".jpg"
                filename = f"anonse{suffix}"
                embed.set_image(url=f"attachment://{filename}")

                image_file = discord.File(io.BytesIO(image_data), filename=filename)
                await interaction.followup.send(embed=embed, view=view, file=image_file)
            else:
                await interaction.followup.send(embed=embed, view=view)

            await self.bot.speech.say(anonse.text, voice="random")
        except Exception as e:
            log.exception(f"Error in anonse command: {e}")
            try:
                await interaction.followup.send("Coś poszło nie tak :(")
            except discord.errors.NotFound as e:
                log.error(f"Failed to send error followup: {e}")

    async def get_anonse(self, cat, region, siurdol) -> Optional[AnonseAd]:
        max_page = await self.get_max_page(cat, region)
        pages = list(range(1, max_page + 1))
        shuffle(pages)

        async def usable_ad(page: int) -> Optional[AnonseAd]:
            anonses = await self.get_anonses(page, cat, region)
            ads = [AnonseAd.from_html(a) for a in anonses]
            if siurdol == "tak":
                ads = [a for a in ads if a.image]
            if not ads:
                return None
            ad = choice(ads)
            log.info(f"ANONSE: page={page}, cat={cat}, {ad}")
            return ad

        return await first_usable(usable_ad, pages[:PAGE_ATTEMPTS])

    async def get_anonses(self, page, cat, region) -> List[AnonseAd]:
        try:
            html = await self.bot.web.text(list_url(page, cat, region))
        except Exception as e:
            log.exception(e)
            return []
        dom = BeautifulSoup(html, "html.parser")
        return dom.find_all("div", {"class": "listaditem"})

    async def get_max_page(self, cat, region) -> int:
        key = (cat, region)
        cached = self._max_pages.get(key)
        if cached and time.monotonic() - cached[0] < MAX_PAGE_TTL:
            return cached[1]
        try:
            html = await self.bot.web.text(list_url(1, cat, region))
        except Exception as e:
            log.exception(e)
            return DEFAULT_MAX_PAGE
        dom = BeautifulSoup(html, "html.parser")
        pagination = dom.find("div", {"class": "pagination"})
        max_page = (
            max(
                int(el.get_text())
                for el in pagination.children
                if el.get_text().isdigit()
            )
            if pagination
            else 1
        )
        self._max_pages[key] = (time.monotonic(), max_page)
        return max_page

    def replace_numbers(self, msg):
        pattern = r"(\d+)[\/,l ]*(\d+)[\/,l ]*(\d+)[\/,l ]?(\d+)?"
        groups = [int(x) for x in re.search(pattern, msg).groups() if x]
        groups = sorted(groups, reverse=True)
        if len(groups) == 3:
            return f"{groups[0]}cm, {groups[1]}lat, siurdol {groups[2]}cm"
        return f"{groups[0]}cm, {groups[1]}kg, {groups[2]}lat, siurdol {groups[3]}cm"


async def setup(bot) -> None:
    await bot.add_cog(Anonse(bot))
