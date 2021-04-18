from bs4 import BeautifulSoup
import requests


class LolCounter:
    def __init__(self):
        self.headers = {'User-Agent': 'Bocek/1.0'}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_lol_counters(self, champion, limit=10):
        url = f'https://www.counterstats.net/league-of-legends/{champion}'
        r = self.session.get(url)
        dom = BeautifulSoup(r.content, 'html.parser')
        tight_dom = dom.find_all('div', {'class': 'champ-box__wrap new'})[0]
        picks = tight_dom.findAll('div', {'class': 'champ-box ALL'})
        best_picks, worst_picks, pop_counters = picks

        champs_perc = self.get_champs_and_percentage(best_picks)
        return champs_perc[:int(limit)]

    def get_champs_and_percentage(self, picks):
        to_ret = []
        champions = picks.findAll('a')
        for champ in champions:
            champ_name = champ['href'].split('/')[-3][3:]
            if perc := champ.find('span', {'class': 'percentage'}):
                percentage = perc.get_text()
            else:
                percentage = champ.find('span').find('b').get_text()
            to_ret.append([champ_name, percentage])
        return to_ret
