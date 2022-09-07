from bs4 import BeautifulSoup
from .log import get_logger
from discord import app_commands, Interaction
from discord.ext import commands
from .common import MyCog
from core.session import Session


log = get_logger(__name__)


class Slang(MyCog, name='slang'):
    def __init__(self, bot):
        self.bot = bot
        headers = {'User-Agent': 'Bocek/1.0'}
        url = 'https://www.miejski.pl'
        self.session = Session(url, headers)

    @app_commands.command(name='slang', description='Losowy miejski.pl')
    async def random_joke(self, interaction: Interaction):
        r = self.session.get('/losuj')
        dom = BeautifulSoup(r.content, 'html.parser')
        article = dom.find('article')
        word = article.find('h1').text
        desc = article.find('p').text.replace('\r\n', '').strip()
        msg = f'{word} - {desc}'
        log.info(msg)
        if interaction.user.voice:
            tts = await self.bot.tts.create_tts(msg, 'pl')
            await interaction.response.send_message(msg)
            await self.bot.play_on_channel(tts)
        else:
            msg = (f'{interaction.user.name}, nie jesteś nawet na kanale...')
            await interaction.response.send_message(msg)
