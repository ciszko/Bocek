from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from random import choice, shuffle
from typing import TYPE_CHECKING, List, Optional

import discord
from bs4 import BeautifulSoup
from discord import Interaction, app_commands
from discord.app_commands import Choice
from discord.ext.commands import Cog

from utils.common import RhymeExtension
from utils.log import log
from utils.session import Session

if TYPE_CHECKING:
    from bot import MyBot

BASE_URL = "https://anonse.inaczej.pl"

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
        headers = {"User-Agent": "Bocek/1.0"}
        self.session = Session(BASE_URL, headers)

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
            await interaction.message.edit(embed=self.embed, view=self)
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
            anonse = await self.get_anonse(interaction, kategoria, region, siurdol)
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
            embed.set_image(url=anonse.image)
            embed.set_footer(text=anonse.footer)
            embed.timestamp = anonse.date

            view = (
                Anonse.DeleteImageButton(
                    msg=anonse.text, img=anonse.image, embed=deepcopy(embed)
                )
                if anonse.image
                else discord.utils.MISSING
            )

            await interaction.followup.send(embed=embed, view=view)
            tts = await self.bot.tts.create_tts(anonse.text, random=True)
            await self.bot.play_on_channel(tts)
        except Exception as e:
            log.exception(f"Error in anonse command: {e}")
            try:
                await interaction.followup.send("Coś poszło nie tak :(")
            except discord.errors.NotFound as e:
                log.error(f"Failed to send error followup: {e}")

    async def get_anonse(self, interaction, cat, region, siurdol):
        max_page = await self.get_max_page(cat, region)
        pages = list(range(1, max_page + 1))
        shuffle(pages)

        for page in pages[:5]:
            anonses = await self.get_anonses(page, cat, region)
            if not anonses:
                continue
            if siurdol == "tak":
                anonses = [a for a in anonses if AnonseAd.from_html(a).image]
                if not anonses:
                    continue
            anonse_item = choice(anonses)
            anonse_ad = AnonseAd.from_html(anonse_item)

            log.info(f"ANONSE: page={page}, cat={cat}, {anonse_ad}")
            return anonse_ad
        else:
            return await interaction.followup.send(
                "Coś nie mogę znaleźć anonsa :disappointed_relieved:"
            )

    async def get_anonses(self, page, cat, region) -> List[AnonseAd]:
        url = f"/?m=list&pg={page}&cat={cat}"
        if region != "0":
            url += f"{url}&region={region}"
        try:
            r = await self.session.get(url)
            html = r.text
        except Exception as e:
            log.exception(e)
            return []
        dom = BeautifulSoup(html, "html.parser")
        return dom.find_all("div", {"class": "listaditem"})

    async def get_max_page(self, cat, region) -> int:
        url = f"/?m=list&pg=1&cat={cat}"
        if region != "0":
            url += f"{url}&region={region}"
        try:
            r = await self.session.get(url)
            html = r.text
        except Exception as e:
            log.exception(e)
            return 30
        dom = BeautifulSoup(html, "html.parser")
        pagination = dom.find("div", {"class": "pagination"})
        return max(
            int(el.get_text()) for el in pagination.children if el.get_text().isdigit()
        )

    def replace_numbers(self, msg):
        pattern = r"(\d+)[\/,l ]*(\d+)[\/,l ]*(\d+)[\/,l ]?(\d+)?"
        groups = [int(x) for x in re.search(pattern, msg).groups() if x]
        groups = sorted(groups, reverse=True)
        if len(groups) == 3:
            return f"{groups[0]}cm, {groups[1]}lat, siurdol {groups[2]}cm"
        return f"{groups[0]}cm, {groups[1]}kg, {groups[2]}lat, siurdol {groups[3]}cm"


async def setup(bot) -> None:
    await bot.add_cog(Anonse(bot))
