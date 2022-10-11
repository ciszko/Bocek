from enum import Enum
import re
import asyncio
from bs4 import BeautifulSoup
import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from random import choice, randint

from .common import MyCog
from .log import log
from core.session import Session


CategoryChoices = [
    Choice(name='ogolne', value='1'),
    Choice(name='praca - szukam', value='2'),
    Choice(name='seks', value='3'),
    Choice(name='wakacje', value='4'),
    Choice(name='szukam partnera', value='5'),
    Choice(name='mieszkania', value='6'),
    Choice(name='fetysze', value='7'),
    Choice(name='komercyjne', value='8'),
    Choice(name='szukam przyjaciela', value='9'),
    Choice(name='szukam kobiety', value='14'),
    Choice(name='korepetycje', value='16'),
    Choice(name='praca - dam', value='17'),
    Choice(name='widzialem cie', value='18')]

RegionChoices = [
    Choice(name='wszystko', value='0'),
    Choice(name='dolnoslaskie', value='1'),
    Choice(name='kujawsko - pomorskie', value='2'),
    Choice(name='lubelskie', value='3'),
    Choice(name='lubuskie', value='4'),
    Choice(name='łódzkie', value='5'),
    Choice(name='małopolskie', value='6'),
    Choice(name='mazowieckie', value='7'),
    Choice(name='opolskie', value='8'),
    Choice(name='podkarpackie', value='9'),
    Choice(name='podlaskie', value='10'),
    Choice(name='pomorskie', value='11'),
    Choice(name='śląskie', value='12'),
    Choice(name='świętokrzyskie', value='13'),
    Choice(name='warmińsko-mazurskie', value='14'),
    Choice(name='wielkopolskie', value='15'),
    Choice(name='zachodniopomorskie', value='16'),
    Choice(name='cała Polska', value='17'),
    Choice(name='zagranica', value='18')]


class Anonse(MyCog, name='anonse'):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = 'https://anonse.inaczej.pl'
        headers = {'User-Agent': 'Bocek/1.0'}
        self.session = Session(self.base_url, headers)

    class DeleteImageButton(discord.ui.View):
        def __init__(self, *, msg=None, img=None):
            self.msg = msg
            self.img = img
            super().__init__()

        @discord.ui.button(label="Usuń siurdolka", style=discord.ButtonStyle.red, emoji='<:siusiak:283294977969356800>')
        async def on_click(self, interaction: Interaction, button: discord.ui.Button):
            button.disabled = True
            button.label = 'Siurdolek usunięty'
            self.add_item(
                discord.ui.Button(
                    label='Zobacz siurdolka', url=self.img, style=discord.ButtonStyle.green, emoji='<:siusiak:283294977969356800>')
            )
            await interaction.response.edit_message(content=self.msg, view=self)

    @app_commands.command(name='anonse', description='Zwraca losowe gejowe anonse z wybranej kategorii. Default: $anonse "fetysze"')
    @app_commands.describe(kategoria='Kategoria z której szukać anonsa')
    @app_commands.describe(region='Region z którego szukać anonsa')
    @app_commands.choices(kategoria=CategoryChoices)
    @app_commands.choices(region=RegionChoices)
    async def anonse(self,
                     interaction: Interaction,
                     kategoria: app_commands.Choice[str] = '7',
                     region: app_commands.Choice[str] = '0'):
        await interaction.response.defer()
        if interaction.user.voice:
            kategoria = kategoria if type(kategoria) == str else kategoria.value
            region = region if type(region) == str else region.value
            author, loc, date, msg, img = await self.get_anonse(interaction, kategoria, region)
            nl = '\n'
            # add button only when image pops up
            view = Anonse.DeleteImageButton(msg=msg, img=img) if img else discord.utils.MISSING
            text = f'**{author}**    *{loc}*    {date}{nl} {msg}{nl + img if img else ""}'
            await interaction.followup.send(text, view=view)
            tts = await self.bot.tts.create_tts(msg)
            await self.bot.play_on_channel(tts)
        else:
            msg = (f'{interaction.user.name}, nie jesteś nawet na kanale...')
            await interaction.response.send_message(msg)

    async def get_anonse(self, interaction, cat, region):
        for i in [1, 2, 3, 4, 30]:
            page = randint(1, int(30/i))
            anonse_list = await self.get_anonses(page, cat, region)
            if anonse_list:
                anonse_item = choice(anonse_list)
                image = anonse_item.find('a', {'class': 'fancybox'})
                image = f'{self.base_url}/' + image['href'] if image else None
                text = anonse_item.find('div', {'class': 'adcontent'}).get_text().strip()
                author = anonse_item.find('i', {'class': 'icon-user'}).next_sibling.strip()
                location = anonse_item.find('i', {'class': 'icon-location-arrow'}).next_sibling
                date = anonse_item.find('i', {'class': 'icon-calendar'}).next_sibling
                log.info(f'ANONSE: page={page}, cat={cat}, {text}')
                return author, location, date, text, image
        else:
            return await interaction.followup.send('Kurde, zebzdziałem się')

    async def get_anonses(self, page, cat, region):
        url = f'/?m=list&pg={page}&cat={cat}'
        if region != '0':
            url += f'{url}&region={region}'
        for _ in range(3):
            try:
                r = self.session.get(url)
                break
            except Exception:
                await asyncio.sleep(0.5)
                continue
        dom = BeautifulSoup(r.content, 'html.parser')
        return dom.find_all('div', {'class': 'listaditem'})

    def replace_numbers(self, msg):
        pattern = r'(\d+)[\/,l ]*(\d+)[\/,l ]*(\d+)[\/,l ]?(\d+)?'
        groups = [int(x) for x in re.search(pattern, msg).groups() if x]
        groups = sorted(groups, reverse=True)
        if len(groups) == 3:
            return f'{groups[0]}cm, {groups[1]}lat, siurdol {groups[2]}cm'
        return f'{groups[0]}cm, {groups[1]}kg, {groups[2]}lat, siurdol {groups[3]}cm'
