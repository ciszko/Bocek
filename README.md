# Bocek
Discord bot to keep you company
Bocek is intended to run on a single discord server mainly because of the live
League of Legends game commentary that requires some port shenaningans and it's
best to keep it inside a local network.

Bocek consists of completely random and very useful features such as: 
- greeting channel members on connect
- saying stupid shit from time to time
- commenting your plays from live League of Legends game
- generating TTS audio
- providing counter picks for League of Legends
- finding rhymes
- explaining random slang from https://www.miejski.pl
- telling some bad random jokes from https://perelki.net
- controlling exaroton minecraft server

# Table of Contents

- [Setup](#setup)
  - [TTS](#tts)
  - [League of Legeneds Live game commentary](#league-of-legeneds-live-game-commentary)
- [Extra configuration](#extra-configuration)
  - [`pyproject.toml`](#pyprojecttoml)
  - [`glossary`](#glossary)



## Setup
To run Bocek you need to set up a `.env` file in the main directory.
You can find an example in [example.env](example.env).

### TTS
In order to speak Bocek requires a google service account with
[TTS (Text-To-Speech) API](https://console.cloud.google.com/apis/api/texttospeech.googleapis.com)
turned on. The json file can be found under [service accounts](https://console.cloud.google.com/apis/credentials) > service accounts > keys

In addition to that Bocek needs vocal cords, a suitable solution is `ffmpeg`.
You can download it from [the official website](https://www.ffmpeg.org/download.html).

### League of Legeneds Live game commentary
This feature facilitates [Game Client API](https://developer.riotgames.com/docs/lol#game-client-api),
this API basically allows to gather a game data from a current LoL match. 

In my original setup I've used Raspberry Pi in a local network that runs the bot.
Because I play LoL on my PC I needed a make a port accessible so that RPi will be
able to reach the API. Most of the players use Windows, thus here are the necessary steps:

1. Make sure that your PC is visible in the local network. Go to Settings > Network and Internet > click the active connection > Network Profile Type > Private Network > change the visibility
2. Create a TCP firewall rule on a designated port (29999 by default)
3. Configure the port to be accessible in a local network. Open cmd and run the following commands:
```cmd
netsh
interface portproxy
add v4tov4 listenport=29999 listenaddress=0.0.0.0 connectport=2999 connectaddress=127.0.0.1
```
Bocek now should know what is happening in your games but he doesn't know who to track (and insult of course).  
To set it up, edit the players variable inside [pyproject.toml](pyproject.toml).

## Extra configuration

### [`pyproject.toml`](pyproject.toml)
In [pyproject.toml](pyproject.toml) you can find some extra configuration variables.

`lol-game-port` - \(int\) port is used to gather data from live LoL game

`offline-wait` - \(int\) time in between checks if player has entered the game, in seconds

`online-wait` - \(int\) polling time in seconds, when in the game (lower time, more frequent events) 

`players` - \(list\) nicks of players that Bocek will comment about

`event-possibility` - \(dict[str, float]\) determines how likely is Bocek to comment about a certain event 

### [`glossary`](glossary)
This directory consists of glossaries that Bocek uses to talk.

`random_join.json` - random stuff that Bocek says from time to time

`rito.json` - LoL live match commentary

`talk.json` - greeting and commands

`rhymes2.json` - rhymes dictionary