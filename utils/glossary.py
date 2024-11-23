import random
import json
import string
from .common import BASE_DIR
from .log import log


class Glossary:
    def __init__(self, plugin, glossary):
        self.plugin = plugin
        self.glossary_path = BASE_DIR / "glossary" / glossary

    def get_random(self, section="default"):
        glossary = self.get_file_json()
        if section not in glossary:
            return None, None
        to_ret = random.choice(glossary[section])
        placeholders = self.get_placeholders(to_ret)
        log.info(f"{self.plugin.__class__.__name__} -> {section} -> {to_ret}")
        return to_ret, placeholders

    def get_value(self, section, key):
        glossary = self.get_file_json()
        if section not in glossary:
            return None, None
        to_ret = glossary[section].get(key, None)
        placeholders = self.get_placeholders(to_ret)
        log.info(f"{section} -> {to_ret}")
        return to_ret, placeholders

    def get_file_json(self):
        with self.glossary_path.open("r+", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def get_placeholders(self, text):
        return [
            name
            for text, name, spec, conv in string.Formatter().parse(text)
            if name != None
        ]
