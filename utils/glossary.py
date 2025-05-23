import json
import random
import string

from utils.common import BASE_DIR
from utils.log import log


class Glossary:
    def __init__(self, plugin, glossary):
        self.plugin = plugin
        self.glossary_path = BASE_DIR / "glossary" / glossary

    def get_random(self, section="default") -> tuple[str, list[str]]:
        """Returns random line from selected section from a glossary"""
        glossary = self.get_file_json()
        if section not in glossary:
            return None, None
        to_ret = random.choice(glossary[section])
        placeholders = self.get_placeholders(to_ret)
        log.info(f"{self.plugin.__class__.__name__} -> {section} -> {to_ret}")
        return to_ret, placeholders

    def get_value(self, section, key) -> tuple[str, list[str]]:
        """Returns specific key from a dictionary section from a glossary"""
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
        """Returns placeholders from the text"""
        return [
            name
            for text, name, spec, conv in string.Formatter().parse(text)
            if name is not None
        ]
