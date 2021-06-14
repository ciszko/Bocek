import pathlib
from discord.ext import commands
from discord import File
from gtts import gTTS
from google.cloud import texttospeech
import os
import random
from .common import async_wrap
from uuid import uuid4
from .log import get_logger

log = get_logger(__name__)


class Tts(commands.Cog, name='tts'):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.join(pathlib.Path(
            __file__).parent.absolute(), '..', 'mp3')
        self.client = texttospeech.TextToSpeechClient()

    @commands.command(name='tts', help='Wysyła plik z nagraniem. $tts "hejo" <pitch=0> <voice=1> <volume=0> <speaking_rate=0.9>')
    async def tts(self, ctx, text, *args):
        kwargs = self.process_args(args)
        log.info(f'{text}, {kwargs}')
        tts = await self.create_tts(text, **kwargs)

        await ctx.send(file=File(tts))
        await ctx.message.delete()
        await self.delete_tts(tts)

    async def create_tts(self, *args, **kwargs):
        if 'random' in kwargs:
            kwargs.pop('random')
            kwargs = self.get_random_voice()
        if {'pitch', 'voice', 'volume'}.intersection(kwargs):
            return await self.tts_google(*args, **kwargs)
        else:
            return await self.tts_gtts(*args, **kwargs)

    @async_wrap
    def tts_gtts(self, text, lang):
        log.info(text)
        tts = gTTS(text, lang=lang)
        tts_path = os.path.join(self.path, f'{uuid4().hex[:10]}.mp3')
        tts.save(tts_path)
        return tts_path

    @async_wrap
    def tts_google(self, text, lang='pl-PL', pitch=0, voice=1, volume=0, speaking_rate=0.9):
        if not text:
            return

        pitch = int(pitch)
        volume = int(volume)

        if lang.lower() == 'pl':
            lang = 'pl-PL'

        if not -20 <= pitch <= 20:
            log.warn(f'Wrong pitch value: {pitch}')
            text = 'Ej człeniu, picz może być od minus dwudziestu do plus dwudziestu'

        if str(voice) not in ['0', '1', '2', '3', 'gothic']:
            log.warn(f'Wrong voice value: {voice}')
            text = 'Wybrałeś zły głos'
            voice = 1

        if type(voice) is str:
            if voice.lower() == 'gothic':
                voice = 1
                pitch = -18
            else:
                voice = getattr(texttospeech.SsmlVoiceGender, voice)
        else:
            voice = int(voice)

        log.info(
            f'pitch={pitch}, voice={voice}, volume={volume}, speaking_rate={speaking_rate}')

        text = texttospeech.SynthesisInput(text=text)
        # voice creation
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang, ssml_gender=voice
        )
        # additionial params
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=pitch,
            volume_gain_db=volume,
            speaking_rate=speaking_rate
        )
        # generate response
        response = self.client.synthesize_speech(
            input=text, voice=voice, audio_config=audio_config
        )
        # save the response
        tts_path = os.path.join(self.path, f'{uuid4().hex[:10]}.mp3')
        with open(tts_path, 'wb') as out:
            out.write(response.audio_content)
        return tts_path

    @async_wrap
    def delete_tts(self, path):
        os.remove(path)
        return

    def get_random_voice(self, **kwargs):
        return {**kwargs,
                'voice': random.randint(0, 3),
                'pitch': random.randrange(-20, 20)
                }

    def process_args(self, args):
        kwargs = {'lang': 'pl-PL',
                  'pitch': 0,
                  'voice': 1,
                  'volume': 0,
                  'speaking_rate': 0.9}
        for arg in args:
            arg, value = arg.split('=')
            if arg not in kwargs.keys():
                continue
            kwargs[arg] = value
        return kwargs
