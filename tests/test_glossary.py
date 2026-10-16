import json
from types import SimpleNamespace

import pytest

from utils.glossary import RHYME, Glossary


@pytest.fixture
def glossary(tmp_path):
    path = tmp_path / "g.json"
    path.write_text(
        json.dumps(
            {
                "greetings": ["Hello {user}!"],
                "group": ["{user} and {all_users}"],
                "plain": ["no placeholders"],
                "rhymes": ["{user} {rhyme:user} {rhyme:baron}"],
            }
        ),
        encoding="utf-8",
    )
    plugin = SimpleNamespace(get_rhyme=lambda word: f"<{word}>")
    return Glossary(plugin, str(path))


def test_render_substitutes_context(glossary):
    assert glossary.render("greetings", user="Ala") == "Hello Ala!"


def test_render_substitutes_multiple_placeholders(glossary):
    assert glossary.render("group", user="A", all_users="A, B") == "A and A, B"


def test_render_ignores_unused_context(glossary):
    assert glossary.render("plain", user="Ala") == "no placeholders"


def test_render_missing_placeholder_raises_clear_error(glossary):
    with pytest.raises(ValueError, match="user"):
        glossary.render("greetings")


def test_render_rhyme_placeholder_uses_context_or_literal(glossary):
    assert glossary.render("rhymes", user="Ala") == "Ala <Ala> <baron>"


def test_render_unknown_section_returns_none(glossary):
    assert glossary.render("nope", user="Ala") is None


def test_shipped_glossaries_only_use_known_placeholders():
    from utils.common import BASE_DIR

    known = {"user", "all_users"}
    for path in (BASE_DIR / "glossary").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for section in data.values():
            lines = section if isinstance(section, list) else []
            for line in lines:
                if not isinstance(line, str):
                    continue
                line = RHYME.sub("", line)
                placeholders = Glossary(object(), str(path)).get_placeholders(line)
                assert set(placeholders) <= known, (path.name, line)
