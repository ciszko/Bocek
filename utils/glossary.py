import json
import random
import string

from utils.common import BASE_DIR
from utils.log import log


class Glossary:
    def __init__(self, plugin, glossary):
        self.plugin = plugin
        self.glossary_path = BASE_DIR / "glossary" / glossary

    def get_random(self, section="default", mood: str | None = None) -> tuple[str | None, list[str] | None]:
        """Returns random line from selected section from a glossary.

        If mood is given, tries '<section>.<mood>' first and falls back to '<section>'.
        """
        glossary = self.get_file_json()
        key = section
        if mood:
            mood_key = f"{section}.{mood}"
            if mood_key in glossary:
                key = mood_key
        if key not in glossary:
            return None, None
        to_ret = random.choice(glossary[key])
        placeholders = self.get_placeholders(to_ret)
        log.info(f"{self.plugin.__class__.__name__} -> {key} -> {to_ret}")
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
