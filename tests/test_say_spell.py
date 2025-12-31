"""Tests for say_spell syllable substitution."""

from mud.skills.say_spell import say_spell


def test_say_spell_basic():
    """Test basic syllable substitution."""
    actual, garbled = say_spell(None, "fireball")

    assert "fireball" in actual
    assert "fireball" not in garbled
    assert len(garbled) > 0


def test_say_spell_bless():
    """Test 'bless' converts to 'fido' per syllable table."""
    actual, garbled = say_spell(None, "bless")

    assert "bless" in actual
    assert "fido" in garbled.lower()


def test_say_spell_empty():
    """Test empty spell name."""
    actual, garbled = say_spell(None, "")

    assert actual == ""
    assert garbled == ""


def test_say_spell_light():
    """Test 'light' converts to 'dies' per syllable table."""
    actual, garbled = say_spell(None, "light")

    assert "light" in actual
    assert "dies" in garbled.lower()
