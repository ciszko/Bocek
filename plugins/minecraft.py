import asyncio
from discord.ext import commands
from functools import cached_property

from .common import MyCog
from .log import get_logger
from core.session import Session

log = get_logger(__name__)


class Minecraft(MyCog, name='minecraft'):
    def __init__(self, bot):
        self.bot = bot
        base_url = 'https://api.exaroton.com/v1'
        token = 'KPl47p7jwWo9hWdW2oz4U8qI4AGY4lBWtZnGY223BwAs91Zeic90T5yEEBe2tjJylI2yvkmNaXtCBFgGPAKLKJ11pIt94M3LrVTU'
        headers = {'User-Agent': 'Bocek/1.0', 'Authorization': f'Bearer {token}'}
        self.session = Session(base_url, headers)

    @cached_property
    def server_id(self):
        resp = self.session.get('/servers').json()
        return next(s['id'] for s in resp['data'] if s['name'] == 'Xubek')

    @commands.command(name='minecraft_start', help='Startuje serwer minkraft')
    async def minecraft_start(self, ctx):
        resp = self.session.get(f'/servers/{self.server_id}/start').json()
        if resp['success'] is False:
            await ctx.message.reply('Kurde, nie mogę włączyć serwerka :(')
            return
        await ctx.message.reply('Serwer minkraft działa!')

    @commands.command(name='minecraft_stop', help='Stopuje serwer minkraft')
    async def minecraft_stop(self, ctx):
        resp = self.session.get(f'/servers/{self.server_id}/stop').json()
        if resp['success'] is False:
            await ctx.message.reply('Kurde, nie mogę wyłączyć serwerka :(')
            return
        await ctx.message.reply('Serwer minkraft zamknięty!')
