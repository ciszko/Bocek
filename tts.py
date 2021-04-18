import pathlib
from gtts import gTTS
import os


class TTS:
    def __init__(self):
        self.path = pathlib.Path(__file__).parent.absolute()

    def create_tts(self, text, lang):
        tts = gTTS(text, lang=lang)
        tts_path = os.path.join(self.path, 'tts.mp3')
        tts.save(tts_path)
        return tts_path

    def delete_tts(self):
        os.remove(os.path.join(self.path, 'tts.mp3'))
        return
