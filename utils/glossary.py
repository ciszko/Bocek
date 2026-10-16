import json
import random
import re
import string

from utils.common import BASE_DIR
from utils.log import log

RHYME = re.compile(r"\{rhyme:([^}]+)\}")


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

    def render(self, section="default", **context) -> str | None:
        """Returns a random line from a section with placeholders filled from context.

        `{rhyme:word}` is replaced by a rhyme from the plugin's get_rhyme."""
        text, _ = self.get_random(section)
        if text is None:
            return None
        # {rhyme:word} rhymes a literal word, or a context value when `word` is a key
        text = RHYME.sub(
            lambda m: str(self.plugin.get_rhyme(context.get(m[1], m[1]))), text
        )
        placeholders = self.get_placeholders(text)
        if missing := [p for p in placeholders if p not in context]:
            raise ValueError(f"Missing placeholders for '{section}': {missing}")
        return text.format_map(context)

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
