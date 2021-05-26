import random
import json
from .common import BASEDIR, async_wrap


class Glossary:
    def __init__(self, plugin, glossary):
        self.plugin = plugin
        self.glossary_path = f'{BASEDIR}/glossary/{glossary}'

    @async_wrap
    def get_random(self, section='default', **kwargs):
        glossary = self.get_file_json()
        if glossary:
            to_ret = random.choice(glossary[section])
            to_ret = self.replace_placeholders(to_ret, **kwargs)
            return to_ret

    @async_wrap
    def get_value(self, section, key, user=None, all_users=None):
        glossary = self.get_file_json()
        if glossary:
            return glossary[section].get(key)

    def get_file_json(self):
        with open(self.glossary_path, 'r+', encoding='utf-8') as f:
            data = json.loads(f)
        return data

    def replace_placeholders(text, **kwargs):
        if user in kwargs:
            text = text.replace('%user%', user)
        if all_users in kwargs:
            all_users = ", ".join(all_users)
            text = text.replace('%all%', all_users)
        return text
