import pathlib
from gtts import gTTS
import os
from .common import async_wrap


class TTS:
    def __init__(self):
        self.path = pathlib.Path(__file__).parent.absolute()

    @async_wrap
    def create_tts(self, text, lang):
        tts = gTTS(text, lang=lang)
        tts_path = os.path.join(self.path, 'tts.mp3')
        tts.save(tts_path)
        return tts_path

    @async_wrap
    def delete_tts(self):
        os.remove(os.path.join(self.path, 'tts.mp3'))
        return
