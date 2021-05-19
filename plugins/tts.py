import pathlib
from gtts import gTTS
import os
from .common import async_wrap
from uuid import uuid4


class TTS:
    def __init__(self):
        self.path = os.path.join(pathlib.Path(
            __file__).parent.absolute(), '..', 'mp3')

    @async_wrap
    def create_tts(self, text, lang):
        tts = gTTS(text, lang=lang)
        tts_path = os.path.join(self.path, f'{uuid4().hex[:10]}.mp3')
        tts.save(tts_path)
        return tts_path

    @async_wrap
    def delete_tts(self, path):
        os.remove(path)
        return
