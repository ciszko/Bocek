import os
import pathlib
import tomllib
from collections.abc import Mapping

from utils.log import log

BASE_DIR = pathlib.Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.toml"
EXAMPLE_PATH = BASE_DIR / "config.example.toml"


def load_config(
    path: pathlib.Path = CONFIG_PATH,
    env: Mapping[str, str] = os.environ,
    example_path: pathlib.Path = EXAMPLE_PATH,
) -> dict:
    """Load config.toml (falling back to the example) and apply env overrides."""
    if not path.exists():
        log.warning(f"{path.name} not found, using {example_path.name}")
        path = example_path
    with path.open("rb") as f:
        config = tomllib.load(f)
    rito = config.setdefault("rito", {})
    if ip := env.get("LOL_GAME_IP"):
        rito["lol-game-ip"] = ip
    if port := env.get("LOL_GAME_PORT"):
        rito["lol-game-port"] = int(port)
    return config


CONFIG = load_config()
