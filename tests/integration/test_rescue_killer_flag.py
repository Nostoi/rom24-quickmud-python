"""`do_rescue` must flag a clan PC rescuer KILLER when it joins a PvP fight.

FIGHT-030 — ROM `do_rescue` calls ``check_killer(ch, fch)`` (`src/fight.c:3097`)
between the two ``stop_fighting`` and the two ``set_fighting`` calls
(`src/fight.c:3094-3099`). When the rescued ally is fighting **another PC**
(``fch`` is not an NPC), the rescuer joins that PvP fight and ROM flags it with
``PLR_KILLER`` + killer timer exactly as ``do_kill``/``do_murder`` would.

``do_rescue``'s only kill-stealing guard (`src/fight.c:3075`, Python
`combat.py:do_rescue`) is **NPC-gated** — it blocks only when ``fch`` is an NPC
and the rescuer is not grouped with the victim. So a PC-vs-PC rescue proceeds,
which is precisely the case ``check_killer`` exists to flag. The Python port
performed the ``stop_fighting``/``set_fighting`` swap but skipped
``check_killer``, so the rescuer escaped the PK consequences ROM imposes.

The placement is load-bearing: ``check_killer`` must run **before**
``set_fighting(caster, foe)`` — its ``attacker.fighting is resolved_victim``
guard (`engine.py:1291`) early-returns once the rescuer is already fighting the
foe, so flagging after the swap would silently never fire.
"""

from __future__ import annotations

import pytest

from mud.commands import process_command
from mud.models.constants import PlayerFlag, Position
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def test_rescue_against_pc_foe_flags_rescuer_killer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:3097 — check_killer(ch, fch) flags the rescuer when
    # it joins combat against a PC foe. Proven check_killer-firing recipe
    # (test_combat.py::test_kill_flags_player_as_killer): clan member + desc set.
    initialize_world("area/area.lst")
    rescuer = create_test_character("Rescuer", 3001)
    ally = create_test_character("Ally", 3001)
    foe = create_test_character("Foe", 3001)

    rescuer.desc = object()
    foe.desc = object()
    rescuer.clan = 1  # is_clan(ch) gate in check_killer (engine.py:1284)
    rescuer.skills["rescue"] = 100
    rescuer.wait = 0

    # Ally is the tank under attack by another PC (foe). No grouping needed:
    # the kill-stealing guard is NPC-gated, so a PC-vs-PC rescue proceeds.
    ally.fighting = foe
    ally.position = int(Position.FIGHTING)
    foe.fighting = ally
    foe.position = int(Position.FIGHTING)

    # Force the rescue skill check to succeed so the swap + check_killer fire.
    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    process_command(rescuer, "rescue ally")

    # The rescue actually ran (tank swap) — so a missing KILLER flag can only mean
    # check_killer wasn't called, not that the rescue silently bailed.
    assert rescuer.fighting is foe, "rescuer did not take over the fight"
    assert foe.fighting is rescuer, "foe was not re-targeted onto the rescuer"
    assert ally.fighting is None, "rescued ally was not pulled out of combat"

    # Primary contract (FIGHT-030): the rescuer is now a KILLER. State bit is
    # delivery-channel-independent — assert it directly.
    assert rescuer.act & int(PlayerFlag.KILLER), "rescuer was not flagged PLR_KILLER"
    # Secondary: the ROM notification line (test chars have no connection, so
    # _push_message lands it in .messages — same as the do_kill flag test).
    assert "*** You are now a KILLER!! ***" in rescuer.messages


def test_rescue_against_npc_foe_does_not_flag_rescuer(monkeypatch: pytest.MonkeyPatch) -> None:
    # mirrors ROM src/fight.c:1240-1243 — check_killer returns early when the foe
    # is an NPC. Rescuing an ally from a mob (the common case) must NOT flag the
    # rescuer; the PvP-only placement is what protects this.
    initialize_world("area/area.lst")
    rescuer = create_test_character("Rescuer", 3001)
    ally = create_test_character("Ally", 3001)
    mob = create_test_character("Ogre", 3001)
    mob.is_npc = True

    rescuer.clan = 1
    rescuer.skills["rescue"] = 100
    rescuer.wait = 0

    # NPC foe → the kill-stealing guard fires unless rescuer + ally are grouped.
    ally.leader = rescuer
    ally.fighting = mob
    ally.position = int(Position.FIGHTING)
    mob.fighting = ally
    mob.position = int(Position.FIGHTING)

    monkeypatch.setattr(rng_mm, "number_percent", lambda: 1)

    process_command(rescuer, "rescue ally")

    # Rescue ran (so this is a real no-flag, not a bailed-out rescue)...
    assert rescuer.fighting is mob, "rescuer did not take over the fight"
    assert mob.fighting is rescuer
    # ...but no KILLER flag, because the foe is an NPC.
    assert not (int(rescuer.act) & int(PlayerFlag.KILLER))
    assert "*** You are now a KILLER!! ***" not in rescuer.messages
