"""Integration tests for ROM-parity `do_steal` (act_obj.c:2161-2330)."""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.commands.thief_skills import do_steal
from mud.models.constants import (
    AffectFlag,
    ExtraFlag,
    ItemType,
    PlayerFlag,
    Position,
    WearLocation,
)
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def _init_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def room():
    from mud.models.room import Room

    if 3001 not in room_registry:
        room_registry[3001] = Room(vnum=3001, name="Test", description="d")
    r = room_registry[3001]
    r.contents.clear()
    r.people.clear()
    yield r
    r.contents.clear()
    r.people.clear()


def _make_thief(movable_char_factory, level: int = 30, *, clan: int = 1, skill: int = 100):
    thief = movable_char_factory("Thief", 3001, points=200)
    thief.is_npc = False
    thief.level = level
    thief.skills["steal"] = skill
    thief.clan = clan
    thief.gold = 0
    thief.silver = 0
    thief.act = 0
    return thief


def _make_victim(
    movable_char_factory,
    *,
    name: str = "Victim",
    level: int = 30,
    is_npc: bool = True,
    gold: int = 0,
    silver: int = 0,
    position: Position = Position.STANDING,
    clan: int = 0,
):
    victim = movable_char_factory(name, 3001, points=200)
    victim.is_npc = is_npc
    victim.level = level
    victim.gold = gold
    victim.silver = silver
    victim.position = position
    victim.clan = clan
    return victim


# ---------------------------------------------------------------------------
# STEAL-001: missing argument
# ---------------------------------------------------------------------------
def test_steal_missing_args_returns_rom_prompt(movable_char_factory, room):
    thief = _make_thief(movable_char_factory)
    assert do_steal(thief, "").startswith("Steal what from whom?")
    assert do_steal(thief, "coins").startswith("Steal what from whom?")


# ---------------------------------------------------------------------------
# STEAL-002: target == self -> "That's pointless."
# ---------------------------------------------------------------------------
def test_steal_from_self_is_pointless(movable_char_factory, room):
    thief = _make_thief(movable_char_factory)
    out = do_steal(thief, "coins thief")
    assert "pointless" in out.lower()


# ---------------------------------------------------------------------------
# STEAL-003: kill-stealing prevented on fighting NPC
# ---------------------------------------------------------------------------
def test_steal_from_fighting_npc_rejected(movable_char_factory, room):
    thief = _make_thief(movable_char_factory)
    npc = _make_victim(movable_char_factory, name="Goblin", position=Position.FIGHTING, gold=500)
    out = do_steal(thief, "gold goblin")
    assert "Kill stealing is not permitted" in out


# ---------------------------------------------------------------------------
# STEAL-004: coin theft success and ROM-ordered message ("silver and gold")
# ---------------------------------------------------------------------------
def test_steal_coins_uses_rom_message_order(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30, skill=100)
    npc = _make_victim(movable_char_factory, name="Mark", gold=1000, silver=1000)

    # Force success: percent = 1, number_range -> char_level so both sums > 0
    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: hi)

    out = do_steal(thief, "coins mark")
    # ROM L2291: "%d silver and %d gold coins."
    assert "silver and" in out
    assert "gold coins" in out
    # MAX_LEVEL=60, 1000 * 30 / 60 = 500
    assert thief.gold == 500
    assert thief.silver == 500
    assert npc.gold == 500
    assert npc.silver == 500


def test_steal_coins_no_money_returns_rom_string(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30, skill=100)
    npc = _make_victim(movable_char_factory, name="Pauper", gold=0, silver=0)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: 1)

    out = do_steal(thief, "gold pauper")
    assert "couldn't get any coins" in out


# ---------------------------------------------------------------------------
# STEAL-005: object theft success uses canonical inventory transfer
# ---------------------------------------------------------------------------
def test_steal_item_success_transfers_inventory(movable_char_factory, object_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30)
    npc = _make_victim(movable_char_factory, name="Merchant", level=20)

    gem = object_factory({"vnum": 9991, "name": "ruby gem", "short_descr": "a ruby", "weight": 1, "level": 5})
    npc.add_object(gem)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)

    out = do_steal(thief, "ruby merchant")
    assert "Got it!" in out
    assert "You pocket" in out
    assert gem in thief.inventory
    assert gem not in npc.inventory


# ---------------------------------------------------------------------------
# STEAL-006: ITEM_INVENTORY rejected with "You can't pry it away."
# ---------------------------------------------------------------------------
def test_steal_item_inventory_flag_rejected(movable_char_factory, object_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30)
    npc = _make_victim(movable_char_factory, name="Shop", level=20)

    obj = object_factory(
        {
            "vnum": 9992,
            "name": "trinket",
            "short_descr": "a trinket",
            "weight": 1,
            "level": 5,
            "extra_flags": int(ExtraFlag.INVENTORY),
        }
    )
    npc.add_object(obj)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)

    out = do_steal(thief, "trinket shop")
    assert "can't pry it away" in out
    assert obj in npc.inventory


# ---------------------------------------------------------------------------
# STEAL-007: ITEM_NODROP -> "You can't pry it away."
# ---------------------------------------------------------------------------
def test_steal_item_nodrop_rejected(movable_char_factory, object_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30)
    npc = _make_victim(movable_char_factory, name="Shop", level=20)

    obj = object_factory(
        {
            "vnum": 9993,
            "name": "cursed ring",
            "short_descr": "a cursed ring",
            "weight": 1,
            "level": 5,
            "extra_flags": int(ExtraFlag.NODROP),
        }
    )
    npc.add_object(obj)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)

    out = do_steal(thief, "ring shop")
    assert "can't pry it away" in out


# ---------------------------------------------------------------------------
# STEAL-008: obj.level > char.level -> "You can't pry it away."
# ---------------------------------------------------------------------------
def test_steal_item_too_high_level_rejected(movable_char_factory, object_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=10)
    npc = _make_victim(movable_char_factory, name="Mage", level=20)

    obj = object_factory(
        {
            "vnum": 9994,
            "name": "epic blade",
            "short_descr": "an epic blade",
            "weight": 1,
            "level": 50,
        }
    )
    npc.add_object(obj)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)

    out = do_steal(thief, "blade mage")
    assert "can't pry it away" in out


# ---------------------------------------------------------------------------
# STEAL-009: non-clan PC always fails -> "Oops."
# ---------------------------------------------------------------------------
def test_steal_no_clan_pc_fails(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30, clan=0, skill=100)
    npc = _make_victim(movable_char_factory, name="Mark", gold=1000)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)

    out = do_steal(thief, "gold mark")
    assert "Oops." in out


# ---------------------------------------------------------------------------
# STEAL-010: failure broadcasts TO_VICT and TO_NOTVICT
# ---------------------------------------------------------------------------
def test_steal_failure_broadcasts_to_vict_and_notvict(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30, clan=0)  # force failure via no_clan
    npc = _make_victim(movable_char_factory, name="Mark", gold=100)
    bystander = _make_victim(movable_char_factory, name="Bob")

    # Clear any prior messages
    thief.messages.clear()
    npc.messages.clear()
    bystander.messages.clear()

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)
    # Deterministic yell choice
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: 0)

    do_steal(thief, "gold mark")

    victim_text = "\n".join(npc.messages)
    bystander_text = "\n".join(bystander.messages)
    assert "tried to steal from you" in victim_text
    assert "tried to steal from" in bystander_text and "Mark" in bystander_text


# ---------------------------------------------------------------------------
# STEAL-011: failure removes AFF_SNEAK
# ---------------------------------------------------------------------------
def test_steal_failure_strips_sneak(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30, clan=0)
    thief.affected_by = int(AffectFlag.SNEAK)
    npc = _make_victim(movable_char_factory, name="Mark", gold=100)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: 0)

    do_steal(thief, "gold mark")
    assert not (int(thief.affected_by) & int(AffectFlag.SNEAK))


# ---------------------------------------------------------------------------
# STEAL-012: failure on PC->PC sets PLR_THIEF
# ---------------------------------------------------------------------------
def test_steal_failure_pc_to_pc_sets_thief_flag(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30, clan=0)
    pc_victim = _make_victim(movable_char_factory, name="Alice", is_npc=False, gold=100)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: 0)

    do_steal(thief, "gold alice")
    assert int(thief.act) & int(PlayerFlag.THIEF)


# ---------------------------------------------------------------------------
# STEAL-013: WAIT_STATE applied on attempt
# ---------------------------------------------------------------------------
def test_steal_applies_wait_state(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=30, clan=0)
    npc = _make_victim(movable_char_factory, name="Mark", gold=100)
    thief.wait = 0

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: 0)

    do_steal(thief, "gold mark")
    assert thief.wait >= 24


# ---------------------------------------------------------------------------
# STEAL-014: PvP level diff > 7 forces failure
# ---------------------------------------------------------------------------
def test_steal_level_diff_forces_failure_pc_to_pc(movable_char_factory, room, monkeypatch):
    thief = _make_thief(movable_char_factory, level=10, clan=1, skill=100)
    pc_victim = _make_victim(movable_char_factory, name="Alice", is_npc=False, level=25, gold=1000)

    import mud.commands.thief_skills as ts

    monkeypatch.setattr(ts, "number_percent", lambda: 1)
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: 0)

    out = do_steal(thief, "gold alice")
    assert "Oops." in out
    assert thief.gold == 0
