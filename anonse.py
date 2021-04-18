from bs4 import BeautifulSoup
import requests
from random import choice


class Anonse:
    def __init__(self):
        self.headers = {'User-Agent': 'Bocek/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_random_anonse(self, page=1):
        url = f'https://anonse.inaczej.pl/?m=list&pg={page}&cat=1'
        r = self.session.get(url)
        dom = BeautifulSoup(r.content, 'html.parser')
        ads = dom.find_all('div', {'class': 'adcontent'})
        return choice([x.get_text().strip() for x in ads])
