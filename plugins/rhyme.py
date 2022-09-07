import json
from discord import app_commands, Interaction
from discord.ext import commands
from .common import BASEDIR
import random
from .log import get_logger


log = get_logger(__name__)


class Rhyme(commands.Cog, name='rhyme'):
    def __init__(self, bot):
        self.bot = bot
        self.dict_path = f'{BASEDIR}/glossary/rhymes2.json'
        with open(self.dict_path, 'r', encoding='utf-8') as dict_json:
            self.rhyme_dict = json.load(dict_json)

    def get_rhyme(self, word, limit=5):
        all_results = set()
        for i in range(len(word) - 1):
            if not (2 <= len(word) - i <= 5):
                continue
            ending = word[i:]
            if result := self.rhyme_dict.get(ending, None):
                if result := [x for x in result if x != word]:
                    population = limit if len(result) > limit else len(result)
                    all_results.update(set(random.sample(result, population)))
                if len(all_results) > limit:
                    break
        return list(all_results)[:limit]

    @app_commands.command(name='rym', description='Zwraca rymy do słowa. Np. $rym dupa 5')
    async def rhyme(self, interaction, word: str, limit: int = 10):
        rhymes = self.get_rhyme(word, limit)
        formatted = ', '.join(rhymes)
        response = f'Rymy do słowa "**{word}**":\n{formatted}'
        await interaction.response.send_message(response)
