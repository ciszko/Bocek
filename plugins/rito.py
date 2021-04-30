from riotwatcher import LolWatcher, ApiError


class Rito():
    def __init__(self):
        self.lol = LolWatcher('RGAPI-5b1d63b7-a22c-4426-9fac-0aef8e02de67')
        self.region = 'eun1'


rito = Rito()
