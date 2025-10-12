import pytest

from mud.game_loop import weather
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.skills import handlers as skill_handlers


def _make_room(vnum: int = 3050) -> Room:
    return Room(vnum=vnum, name=f"Room {vnum}")


def test_ventriloquate_broadcasts_fake_voice(monkeypatch) -> None:
    caster = Character(name="Illusionist", level=42, is_npc=False)
    speaker = Character(name="Guard", level=30, is_npc=False)
    believer = Character(name="Believer", level=25, is_npc=False)

    room = _make_room()
    for char in (caster, speaker, believer):
        room.add_character(char)
        char.messages.clear()

    def always_fail(_level, _victim, _damage_type) -> bool:
        return False

    monkeypatch.setattr(skill_handlers, "saves_spell", always_fail)

    assert skill_handlers.ventriloquate(caster, "Guard hello there") is True

    expected = "Guard says 'hello there'."
    assert caster.messages[-1] == expected
    assert believer.messages[-1] == expected
    assert speaker.messages == []


def test_ventriloquate_reveals_spoof_on_save(monkeypatch) -> None:
    caster = Character(name="Trickster", level=36, is_npc=False)
    speaker = Character(name="Mayor", level=32, is_npc=False)
    gullible = Character(name="Gullible", level=20, is_npc=False)
    skeptic = Character(name="Skeptic Citizen", level=20, is_npc=False)

    room = _make_room(3051)
    for char in (caster, speaker, gullible, skeptic):
        room.add_character(char)
        char.messages.clear()

    def selective_save(_level, victim, _damage_type) -> bool:
        return getattr(victim, "name", "") == "Skeptic Citizen"

    monkeypatch.setattr(skill_handlers, "saves_spell", selective_save)

    assert skill_handlers.ventriloquate(caster, "Mayor welcome adventurers") is True

    fooled = "Mayor says 'welcome adventurers'."
    reveal = "Someone makes Mayor say 'welcome adventurers'."

    assert gullible.messages[-1] == fooled
    assert skeptic.messages[-1] == reveal
    assert caster.messages[-1] == fooled
    assert speaker.messages == []

    skeptic.position = Position.SLEEPING
    skeptic.messages.clear()
    monkeypatch.setattr(skill_handlers, "saves_spell", lambda *_: False)

    assert skill_handlers.ventriloquate(caster, "Mayor whispering winds") is True
    assert skeptic.messages == []


def test_control_weather_makes_weather_better(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Druid", level=24, is_npc=False)
    caster.messages.clear()

    original_change = weather.change
    weather.change = 0

    def fake_dice(number: int, size: int) -> int:
        assert number == c_div(caster.level, 3)
        assert size == 4
        return 9

    monkeypatch.setattr(skill_handlers.rng_mm, "dice", fake_dice)

    try:
        assert skill_handlers.control_weather(caster, "better") is True
        assert weather.change == 9
        assert caster.messages[-1] == "Ok."
    finally:
        weather.change = original_change


def test_control_weather_makes_weather_worse(monkeypatch: pytest.MonkeyPatch) -> None:
    caster = Character(name="Weatherwitch", level=30, is_npc=False)
    caster.messages.clear()

    original_change = weather.change
    weather.change = 5

    def fake_dice(number: int, size: int) -> int:
        assert number == c_div(caster.level, 3)
        assert size == 4
        return 7

    monkeypatch.setattr(skill_handlers.rng_mm, "dice", fake_dice)

    try:
        assert skill_handlers.control_weather(caster, "worse") is True
        assert weather.change == 5 - 7
        assert caster.messages[-1] == "Ok."
    finally:
        weather.change = original_change
