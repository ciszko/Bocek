import random
import json
from .common import BASEDIR
from .log import get_logger

log = get_logger(__name__)


class Glossary:
    def __init__(self, plugin, glossary):
        self.plugin = plugin
        self.glossary_path = f'{BASEDIR}/glossary/{glossary}'

    def get_random(self, section='default', **kwargs):
        glossary = self.get_file_json()
        if section not in glossary:
            return None
        to_ret = random.choice(glossary[section])
        to_ret = self.replace_placeholders(to_ret, **kwargs)
        log.info(f'{self.plugin.__class__.__name__} -> {section} -> {to_ret}')
        return to_ret

    def get_value(self, section, key, **kwargs):
        glossary = self.get_file_json()
        if section not in glossary:
            return None
        to_ret = glossary[section].get(key, None)
        to_ret = self.replace_placeholders(to_ret, **kwargs)
        log.info(f'{section} -> {to_ret}')
        return to_ret

    def get_file_json(self):
        with open(self.glossary_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def replace_placeholders(self, text, **kwargs):
        if 'user' in kwargs:
            text = text.replace('%user%', kwargs['user'])
        if 'all_users' in kwargs:
            all_users = kwargs['all_users']
            text = text.replace('%all%', all_users)
        return text
