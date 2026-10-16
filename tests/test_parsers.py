from pathlib import Path

import pytest

from cogs.joke import parse_joke
from cogs.slang import parse_slang

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_joke_returns_joke_text_only():
    assert parse_joke(fixture("joke.html")) == (
        "Idzie baba do lekarza. Lekarz pyta: - Co dolega? - Nic, tak wpadłam."
    )


def test_parse_joke_raises_on_unexpected_page():
    with pytest.raises(AttributeError):
        parse_joke("<html><body>nothing here</body></html>")


def test_parse_slang_returns_word_and_definition():
    msg = parse_slang(fixture("slang.html"))
    assert msg.startswith("Szlustydzień - Śląskie określenie na koniec tygodnia")
