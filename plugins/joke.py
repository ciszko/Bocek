from bs4 import BeautifulSoup
from .log import log
from discord import app_commands, Interaction
from discord.ext import commands
from .common import MyCog
from core.session import Session


class Joke(MyCog, name='joke'):
    def __init__(self, bot):
        self.bot = bot
        headers = {'User-Agent': 'Bocek/1.0'}
        url = 'https://perelki.net'
        self.session = Session(url, headers)

    @app_commands.command(name='żart', description='Losowy żarcik')
    async def random_joke(self, interaction: Interaction):
        r = self.session.get('/random')
        dom = BeautifulSoup(r.content, 'html.parser')
        joke = dom.find('div', {'class': 'content'}).find(
            'div', {'class': 'container'}).get_text()
        msg = joke[:joke.find('Dowcip:')].replace(
            '\r', '').replace('\n', ' ').replace('\t', '')
        await interaction.response.send_message(msg)
        if interaction.user.voice:
            tts = await self.bot.tts.create_tts(msg)
            await self.bot.play_on_channel(tts)
