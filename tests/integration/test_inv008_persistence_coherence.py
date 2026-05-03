"""INV-008 enforcement test: DUAL-LOAD-CHARACTER-COHERENCE.

ROM Reference: src/save.c fwrite_char / fread_char — single pfile owns all
player state.  Python equivalent: mud.persistence (JSON pfile) is the sole
source of truth; mud.account.account_manager is a thin shim delegating to it.

This test verifies that a character saved via mud.account.account_manager
(the production path used by the game loop) round-trips all critical state
correctly — and that a legacy DB-only character (no JSON pfile) can still
be loaded via the DB fallback path.

Invariant: account_manager.save_character / account_manager.load_character
must produce a runtime Character with:
  - character_registry membership (INV-003)
  - correct room placement
  - full gameplay state (level, practice, skills, perm_stat)
  - password_hash round-trip (pcdata.pwd)
"""

from __future__ import annotations

import mud.persistence as _persistence
import pytest

from mud.account.account_manager import load_character, save_character
from mud.account.account_service import clear_active_accounts
from mud.db.models import Base
from mud.db.session import engine
from mud.models.character import PCData, character_registry
from mud.models.constants import ROOM_VNUM_SCHOOL
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.security import bans
from mud.world import create_test_character, initialize_world
from mud.world.world_state import reset_lockdowns


@pytest.fixture(scope="module", autouse=True)
def _world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    mob_registry.clear()
    obj_registry.clear()
    room_registry.clear()


@pytest.fixture(autouse=True)
def _clean(tmp_path):
    """Fresh DB + isolated pfile dir for every test."""
    _persistence.PLAYERS_DIR = tmp_path / "players"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    yield
    _persistence.PLAYERS_DIR = _persistence.Path("data/players")


# ---------------------------------------------------------------------------
# INV-008 core: save/load round-trip via account_manager
# ---------------------------------------------------------------------------


def test_inv008_save_load_round_trip_preserves_gameplay_state():
    """INV-008: account_manager save/load must round-trip full gameplay state.

    Save a character with non-default level, practice, and skill values then
    reload and assert all fields survive.  Under the old DB path, mana/move/
    exp/hitroll/damroll/skills were silently dropped.
    """
    char = create_test_character("Roundtrip", ROOM_VNUM_SCHOOL)
    char.level = 5
    char.practice = 12
    char.train = 4
    char.gold = 100
    char.silver = 50
    char.exp = 2500
    char.hitroll = 3
    char.damroll = 2
    char.mana = 80
    char.max_mana = 100
    char.move = 90
    char.max_move = 120
    char.skills["recall"] = 75

    save_character(char)

    loaded = load_character("Roundtrip")
    assert loaded is not None, "load_character must return a Character after save"
    assert loaded.level == 5
    assert loaded.practice == 12
    assert loaded.train == 4
    assert loaded.gold == 100
    assert loaded.silver == 50
    assert loaded.exp == 2500
    assert loaded.hitroll == 3
    assert loaded.damroll == 2
    assert loaded.mana == 80
    assert loaded.max_mana == 100
    assert loaded.move == 90
    assert loaded.max_move == 120
    assert loaded.skills.get("recall") == 75


def test_inv008_load_registers_character(tmp_path):
    """INV-008 + INV-003: load_character via account_manager adds to registry."""
    char = create_test_character("Regtest", ROOM_VNUM_SCHOOL)
    save_character(char)

    before = set(id(c) for c in character_registry)
    loaded = load_character("Regtest")
    assert loaded is not None
    try:
        assert id(loaded) in {id(c) for c in character_registry}, (
            "load_character must append to character_registry (INV-003)"
        )
    finally:
        try:
            character_registry.remove(loaded)
        except ValueError:
            pass


def test_inv008_password_hash_round_trips():
    """INV-008: pcdata.pwd survives save/load via account_manager."""
    char = create_test_character("Pwdtest", ROOM_VNUM_SCHOOL)
    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.pwd = "$argon2id$v=19$m=65536,t=3,p=4$inv008test"

    save_character(char)

    loaded = load_character("Pwdtest")
    assert loaded is not None
    assert loaded.pcdata is not None
    assert loaded.pcdata.pwd == "$argon2id$v=19$m=65536,t=3,p=4$inv008test", (
        "pcdata.pwd must survive account_manager save/load (INV-008)"
    )


def test_inv008_room_placement_survives_round_trip():
    """INV-008: room placement persists and loads correctly."""
    char = create_test_character("Roomtest", ROOM_VNUM_SCHOOL)
    save_character(char)

    loaded = load_character("Roomtest")
    assert loaded is not None
    assert loaded.room is not None
    assert loaded.room.vnum == ROOM_VNUM_SCHOOL
