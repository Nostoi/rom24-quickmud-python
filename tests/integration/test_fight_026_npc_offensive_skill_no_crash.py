"""FIGHT-026 — NPC offensive-skill commands must not crash on a mob caller.

FIGHT-022 added a faithful `mob_hit` whose off-skill dispatch
(`_mob_offensive_skill`) calls the real `do_bash`/`do_kick`/`do_berserk`/
`do_dirt`/`do_trip`/`do_disarm` command handlers on the NPC attacker (ROM
`src/fight.c` `mob_hit` does the same). `do_bash`/`do_kick`/`do_berserk` already
gate NPCs on their `OFF_` flag, but `do_dirt`/`do_trip`/`do_disarm` accessed
`char.skills.get(...)` directly — `MobInstance` has no `skills` dict, so any
flagged mob that rolled those branches crashed with ``AttributeError``.

The crash was latent at FIGHT-022 commit time (no test happened to roll
`skill_roll == 6` for a flagged mob) and was surfaced when FIGHT-024 reordered
the combat tick: the mayor #3143 (OFF_TRIP) then rolled into `do_trip` during
`test_kill_mob_grants_xp_integration` and `do_trip` crashed.

ROM gates these on the `OFF_` flag for NPCs (`if (IS_NPC(ch)) { if (!IS_SET(
ch->off_flags, OFF_*)) return; }`), not a learned percent. These tests pin that
contract: a flagged NPC runs the handler without crashing; an unflagged NPC is
gated out silently. (This closes only the *crash*; per-command RNG-draw fidelity
for flagged mobs is still unverified — see FIGHT_C_AUDIT.md follow-ups.)
"""

from __future__ import annotations

from mud.commands.combat import do_dirt, do_disarm, do_trip
from mud.models.constants import OffFlag
from mud.spawning.mob_spawner import spawn_mob
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def _npc_vs_victim(off_flags: OffFlag):
    rng_mm.seed_mm(777)
    mob = spawn_mob(3064)  # the drunk — a plain mob we re-flag explicitly
    assert mob is not None
    mob.off_flags = int(off_flags)
    victim = create_test_character("Victim", 3008)
    victim.room.add_character(mob)
    mob.fighting = victim
    victim.fighting = mob
    return mob, victim


def test_do_trip_on_npc_with_off_trip_does_not_crash():
    initialize_world()
    mob, _victim = _npc_vs_victim(OffFlag.TRIP)

    # Pre-fix this raised AttributeError: 'MobInstance' object has no attribute
    # 'skills'. ROM-faithful: an OFF_TRIP NPC runs the trip attempt.
    result = do_trip(mob, "")
    assert isinstance(result, str)
    # It must have proceeded past the NPC skill gate (not the "Tripping?" PC path).
    assert result != "Tripping? What's that?"


def test_do_dirt_and_do_disarm_on_npc_do_not_crash():
    initialize_world()
    mob, _victim = _npc_vs_victim(OffFlag.KICK_DIRT | OffFlag.DISARM)

    # Neither handler may raise AttributeError on a MobInstance caller.
    assert isinstance(do_dirt(mob, ""), str)
    assert isinstance(do_disarm(mob, ""), str)


def test_offensive_skills_gated_out_for_unflagged_npc():
    initialize_world()
    # No OFF_ skill flags: ROM gates the NPC out silently ("" return).
    mob, _victim = _npc_vs_victim(OffFlag(0))

    assert do_trip(mob, "") == ""
    assert do_dirt(mob, "") == ""
