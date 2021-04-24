from bs4 import BeautifulSoup
import requests
from unidecode import unidecode
from random import choice, randint


class Anonse:
    def __init__(self):
        self.headers = {'User-Agent': 'Bocek/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.categories = {
            'ogolne': '1',
            'praca - szukam': '2',
            'seks': '3',
            'wakacje': '4',
            'szukam partnera': '5',
            'mieszkania': '6',
            'fetysze': '7',
            'komercyjne': '8',
            'szukam przyjaciela': '9',
            'szukam kobiety': '14',
            'korepetycje': '16',
            'praca - dam': '17',
            'widzialem cie': '18',
        }

    def get_random_anonse(self, cat='fetysze'):
        page = randint(1, 10)
        cat = self.categories[unidecode(cat)]
        url = f'https://anonse.inaczej.pl/?m=list&pg={page}&cat={cat}'
        r = self.session.get(url)
        dom = BeautifulSoup(r.content, 'html.parser')
        ads = dom.find_all('div', {'class': 'adcontent'})
        return choice([x.get_text().strip() for x in ads])
