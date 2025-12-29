"""
Tests for surrender command (ROM fight.c:3222-3242).
"""

from mud.commands.combat import do_surrender
from mud.models.character import Character


def test_surrender_requires_fighting():
    """Surrender command requires being in combat."""
    char = Character(name="TestChar", is_npc=False)
    char.fighting = None

    result = do_surrender(char, "")

    assert "But you're not fighting" in result


def test_surrender_stops_combat():
    """Surrender ends combat for the surrendering character."""
    char = Character(name="TestChar", is_npc=False)
    mob = Character(name="Guard", is_npc=True)

    # Set up combat
    char.fighting = mob
    mob.fighting = char

    result = do_surrender(char, "")

    # Combat should be stopped
    assert char.fighting is None
    assert mob.fighting is None
    assert "You surrender" in result


def test_surrender_to_player():
    """Player surrendering to another player (PvP scenario)."""
    char = Character(name="TestChar", is_npc=False)
    opponent = Character(name="Opponent", is_npc=False)

    # Set up combat
    char.fighting = opponent
    opponent.fighting = char

    result = do_surrender(char, "")

    # Combat should stop, no attack from opponent (player, not NPC)
    assert char.fighting is None
    assert "You surrender" in result
    assert "ignore" not in result  # No NPC ignore message


def test_surrender_message_format():
    """Surrender displays proper ROM-style message."""
    char = Character(name="TestChar", is_npc=False)
    mob = Character(name="Orc", is_npc=True)
    mob.mobprogs = []

    char.fighting = mob

    result = do_surrender(char, "")

    # Should contain opponent's name
    assert "Orc" in result or "orc" in result
    assert "surrender" in result.lower()


def test_npc_surrender():
    """NPC surrendering (edge case, usually mobprog-driven)."""
    mob = Character(name="Guard", is_npc=True)
    char = Character(name="TestChar", is_npc=False)

    # NPC fighting player
    mob.fighting = char

    result = do_surrender(mob, "")

    # Should stop fighting but no special NPC behavior
    # (ROM code only triggers mobprog if !IS_NPC(ch) && IS_NPC(mob))
    assert mob.fighting is None
    assert "surrender" in result.lower()
