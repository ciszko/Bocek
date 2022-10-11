import pathlib
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord import File
from google.cloud import texttospeech
import os
import random
from .common import async_wrap, MyCog
from uuid import uuid4
from .log import log


VOICE_CHOICES = [
    'pl-PL-Wavenet-A',
    'pl-PL-Wavenet-B',
    'pl-PL-Wavenet-C',
    'pl-PL-Wavenet-D',
    'pl-PL-Wavenet-E',
]

VoiceChoices = [
    Choice(name='upośledzona kobieta', value=VOICE_CHOICES[0]),
    Choice(name='bocek', value=VOICE_CHOICES[1]),
    Choice(name='upośledzony', value=VOICE_CHOICES[2]),
    Choice(name='dziecko', value=VOICE_CHOICES[3]),
    Choice(name='kobieta', value=VOICE_CHOICES[4])
]


class Tts(MyCog, name='tts'):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.join(pathlib.Path(
            __file__).parent.absolute(), '..', 'mp3')
        self.client = texttospeech.TextToSpeechClient()

    @app_commands.command(name='tts', description='Wysyła plik z nagraniem.')
    @app_commands.describe(text='Tekst do powiedzenia')
    @app_commands.describe(pitch='Wysokość głosu')
    @app_commands.choices(voice=VoiceChoices)
    @app_commands.describe(volume='Głośność')
    @app_commands.describe(speaking_rate='Szybkość mówienia')
    async def tts(self,
                  interaction: Interaction,
                  text: str,
                  pitch: app_commands.Range[float, -20., 20.] = 0,
                  voice: app_commands.Choice[str] = 'pl-PL-Wavenet-B',
                  volume: app_commands.Range[float, 0., 1.] = 0,
                  speaking_rate: app_commands.Range[float, 0.25, 4.] = 0.9):
        await interaction.response.defer()
        voice = voice if type(voice) == str else voice.value
        tts = await self.create_tts(text, pitch, voice, volume, speaking_rate)

        await interaction.followup.send(file=File(tts))

    async def create_tts(self, *args, **kwargs):
        if 'random' in kwargs:
            kwargs.pop('random')
            kwargs = self.get_random_voice()
        log.info(f'TTS args {args=}, {kwargs=}')
        return await self.tts_google(*args, **kwargs)

    @async_wrap
    def tts_google(self, text, pitch=0.0, voice='pl-PL-Wavenet-B', volume=0.0, speaking_rate=0.9, lang='pl-PL'):
        if not text:
            return

        if lang.lower() == 'pl':
            lang = 'pl-PL'

        # if '<' in text:
        #     text = texttospeech.SynthesisInput(ssml=text)
        # else:
        tts = texttospeech.SynthesisInput(text=text)
        # voice creation
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=lang, name=voice
        )
        # additionial params
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=pitch,
            volume_gain_db=volume,
            speaking_rate=speaking_rate
        )
        # generate response
        try:
            response = self.client.synthesize_speech(
                input=tts, voice=voice_params, audio_config=audio_config
            )
        except Exception as exc:
            log.exception(exc)
            response = self.client.synthesize_speech(
                input=tts, voice=voice_params, audio_config=audio_config
            )
        # save the response
        tts_path = os.path.join(self.path, f'{uuid4().hex[:10]}.mp3')
        with open(tts_path, 'wb') as out:
            out.write(response.audio_content)
        return tts_path

    @async_wrap
    def delete_tts(self, path):
        try:
            os.remove(path)
            log.info(f'Removed {path}')
        except FileNotFoundError:
            log.warning(f'{path} was already deleted')
        return

    @async_wrap
    def delete_all_tts(self):
        log.info('Deleting all tts')
        for file in os.listdir(self.path):
            try:
                os.remove(os.path.join(self.path, file))
            except PermissionError:
                log.warning(f'{file} is still in use')
        return

    def get_random_voice(self, **kwargs):
        return {**kwargs,
                'voice': random.choice(VOICE_CHOICES),
                'pitch': random.uniform(-20, 20),
                'speaking_rate': random.uniform(0.85, 1.0)
                }
