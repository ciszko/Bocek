# Bocek — Project Instructions

## What is Bocek?

Bocek is a Polish-language Discord bot written in Python (3.12), designed for a single private server. It's a fun, voice-capable companion bot with personality. It speaks Polish, uses TTS to talk in voice channels, and provides live League of Legends game commentary among other features.

## Tech Stack

- **Runtime**: Python 3.12, managed with `uv`
- **Framework**: `discord.py` (with voice support)
- **TTS**: Google Cloud Text-to-Speech API (Polish voices)
- **Audio**: `ffmpeg` + `pydub` for playback and effects
- **Web scraping**: `aiohttp` / `niquests` + `BeautifulSoup4`
- **Linter**: `ruff`

## Project Structure

```
bot.py            # Main bot class (MyBot), event handlers, slash commands
cogs/             # Feature modules (discord.py Cogs)
  anonse.py       # Fetches classified ads from anonse.inaczej.pl
  joke.py         # Fetches random jokes from perelki.net
  lol_counter.py  # LoL champion counter-pick lookup (counterstats.net)
  minecraft.py    # Controls an Exaroton Minecraft server via API
  random_event.py # Periodically joins voice and says random stuff
  rhyme.py        # Finds rhymes using a local dictionary
  rito.py         # Live LoL game commentary via Game Client API
  slang.py        # Fetches Polish slang definitions from miejski.pl
  tts.py          # Google Cloud TTS integration + fart sound effects
utils/
  common.py       # Shared constants, helpers, RhymeExtension mixin
  glossary.py     # Loads JSON phrase files from glossary/
  log.py          # Loguru-based logger
  session.py      # Shared aiohttp session wrapper with retry logic
glossary/         # JSON phrase banks used by cogs
  random_join.json
  rito.json       # LoL event commentary lines
  talk.json       # Greetings and command responses
  rhymes2.json    # Rhyme dictionary
farts/            # Fart sound MP3 files used by /pierd command
mp3/              # Runtime directory for generated TTS audio files
pyproject.toml    # Project metadata + bot configuration (rito section)
example.env       # Template for .env secrets
```

## Configuration

### `.env` (secrets — never commit)
See `example.env` for required keys:
- `TOKEN` — Discord bot token
- `VOICE_CHANNEL_ID` / `TEXT_CHANNEL_ID` — channel IDs
- `MINECRAFT_SERVER_TOKEN` — Exaroton API token
- Google service account credentials path

### `pyproject.toml` `[tool.bocek.rito]` section
Runtime tuning (no secrets):
- `lol-game-ip` / `lol-game-port` — Game Client API endpoint (port-forwarded from player PC)
- `offline-wait` / `online-wait` — polling intervals in seconds
- `players` — list of LoL summoner names to track
- `event-possibility` — per-event float probability (0–1) of commenting

## Key Architectural Patterns

- **Cogs**: Each feature lives in its own `Cog` class in `cogs/`. Loaded dynamically on startup from `bot.py:load_cogs()`.
- **RhymeExtension mixin**: Shared across bot and cogs via `utils/common.py`.
- **Glossary**: `Glossary` class loads JSON phrase files and provides `get_random(key)` returning `(phrase, [placeholders])`. Placeholders are substituted with `replace_all()` using `eval()` against a local scope.
- **TTS flow**: Text → Google Cloud TTS → MP3 file → `discord.FFmpegOpusAudio` → voice channel. Files are deleted after playback (except fart sounds).
- **Rito (LoL) cog**: Polls the Game Client API on an interval. Detects events via `DeepDiff` on successive game state snapshots, then probabilistically triggers voice commentary.
- **Session**: All HTTP is done through `utils/session.py` which wraps `niquests` with retry logic.

## Slash Commands

| Command | Cog | Description |
|---------|-----|-------------|
| `/żart` | joke | Random joke from perelki.net |
| `/slang` | slang | Random definition from miejski.pl |
| `/rym <word>` | rhyme | Find rhymes for a Polish word |
| `/counter <champion>` | lol_counter | LoL counter-pick suggestions |
| `/siusiak` | bot.py | Says something about the user's anatomy (TTS) |
| `/anus` | bot.py | Says "anus anus nostradamus" (TTS) |
| `/morda` | bot.py | Stops current TTS playback |
| `/pierd` | bot.py | Plays a random fart sound |
| `/minecraft` | minecraft | Controls the Exaroton server |
| `/anonse` | anonse | Fetches classified ads |

## Message Triggers

- `cześć bocek` (and variants) → bot replies with a greeting
- `bocek huju` → bot says a random phrase from `talk.json["bocek_huju"]` via TTS

## Voice Behavior

- Bot joins voice when a user connects to the configured voice channel → greets them via TTS.
- Bot disconnects when the last human leaves the voice channel.
- All TTS playback goes through `bot.play_on_channel()`.

## Running Locally

```bash
cp example.env .env
# fill in .env
uv run python bot.py
```

## Language Note

The bot's personality and all phrases are in **Polish**. Cog/command names and code are in English. Keep this split when adding features.
