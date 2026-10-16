from utils.config import load_config

EXAMPLE = """
[rito]
lol-game-ip = "127.0.0.1"
lol-game-port = 1
players = ["Example"]

[rito.event-possibility]
Ace = 0.5
"""

REAL = """
[rito]
lol-game-ip = "10.0.0.2"
lol-game-port = 29999
players = ["A", "B"]

[rito.event-possibility]
Ace = 0.9
"""


def test_loads_arrays_and_tables(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(REAL)
    rito = load_config(path, env={}, example_path=tmp_path / "x.toml")["rito"]
    assert rito["players"] == ["A", "B"]
    assert rito["event-possibility"] == {"Ace": 0.9}


def test_falls_back_to_example_when_config_missing(tmp_path):
    example = tmp_path / "config.example.toml"
    example.write_text(EXAMPLE)
    config = load_config(tmp_path / "config.toml", env={}, example_path=example)
    assert config["rito"]["players"] == ["Example"]


def test_env_overrides_game_address(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(REAL)
    env = {"LOL_GAME_IP": "192.168.1.5", "LOL_GAME_PORT": "1234"}
    rito = load_config(path, env=env, example_path=tmp_path / "x.toml")["rito"]
    assert rito["lol-game-ip"] == "192.168.1.5"
    assert rito["lol-game-port"] == 1234


def test_shipped_example_is_valid():
    from utils.config import EXAMPLE_PATH

    rito = load_config(EXAMPLE_PATH, env={})["rito"]
    assert isinstance(rito["players"], list)
    assert all(isinstance(v, float | int) for v in rito["event-possibility"].values())
