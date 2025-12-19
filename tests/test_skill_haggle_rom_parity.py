from __future__ import annotations

from mud.models.character import Character
from mud.skills.handlers import haggle


def make_character(**overrides) -> Character:
    base = {
        "name": overrides.get("name", "tester"),
        "level": overrides.get("level", 20),
        "skills": overrides.get("skills", {}),
    }
    char = Character(**base)
    for key, value in overrides.items():
        setattr(char, key, value)
    return char


def test_haggle_is_not_a_command():
    """ROM L2601-2933: Haggle is passive, checked during shop transactions."""
    char = make_character(skills={"haggle": 75})

    result = haggle(char)

    assert result["success"] is False
    assert "passive" in result["message"].lower()


def test_haggle_returns_dict():
    """Haggle handler returns dict for consistency."""
    char = make_character()

    result = haggle(char)

    assert isinstance(result, dict)
    assert "success" in result
    assert "message" in result


def test_haggle_explains_usage():
    """Message explains haggle is used automatically."""
    char = make_character()

    result = haggle(char)

    assert (
        "shop" in result["message"].lower() or "buy" in result["message"].lower() or "sell" in result["message"].lower()
    )
