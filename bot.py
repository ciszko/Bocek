import os
from discord.ext.commands import Bot
import discord
from dotenv import load_dotenv
import random
from scrape import LolCounter
from tts import TTS
from anonse import Anonse
from time import sleep

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('GUILD_ID')


class MyBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lol_counter = LolCounter()
        self.gtts = TTS()
        self.anonse = Anonse()


bot = MyBot(command_prefix='$')

channel_list = []


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    for channel in bot.get_all_channels():
        channel_list.append(channel)


@bot.command()
async def siusiak(ctx):
    types = ['potężnego', 'małego', 'brudnego',
             'paskudnego', 'ślicznego', 'krzywego', 'obszczanego']
    response = f'{ctx.author.name} ma {random.choice(types)} siusiaka'
    await ctx.send(response)
    await ctx.message.delete()


@bot.command()
async def counter(ctx, arg):
    counters = bot.lol_counter.get_lol_counters(arg)

    response = '\n'.join(f'{x}: {y}' for x, y in counters)
    await ctx.send(response)
    await ctx.message.delete()


@bot.command()
async def tts(ctx, arg):
    tts = bot.gtts.create_tts(arg, 'pl')

    await ctx.send(file=discord.File(tts))
    await ctx.message.delete()


@bot.command()
async def anonse(ctx):
    # Gets voice channel of message author
    voice_channel = ctx.author.voice.channel
    channel = None
    anonse = bot.anonse.get_random_anonse()
    tts = bot.gtts.create_tts(anonse, 'pl')
    if voice_channel != None:
        channel = voice_channel.name
        vc = await voice_channel.connect()
        vc.play(discord.FFmpegPCMAudio(
            executable="D:/Projekt/Bocek/extras/ffmpeg.exe", source=tts))
        # Sleep while audio is playing.
        while vc.is_playing():
            sleep(.1)
        await vc.disconnect()
    else:
        await ctx.send(str(ctx.author.name) + "is not in a channel.")
    # Delete command after the audio is done playing.
    await ctx.message.delete()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    msg = message.content.lower()

    greetings = ['cześć bocek', 'czesc bocek', 'czesć bocek', 'cześc bocek']

    if any(x in msg for x in greetings):
        await message.channel.send(f'Siemano {message.author.name}!')

    elif msg == 'bocek huju':
        to_choose = ['paruwo', 'obżydronie', 'obszczańcu', 'kutfo']
        await message.channel.send(f'{message.author.name} {random.choice(to_choose)}', tts=True)

    await bot.process_commands(message)


bot.run(TOKEN)
