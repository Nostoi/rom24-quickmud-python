"""INV-008 enforcement test: DB-CANONICAL persistence.

ROM Reference: src/save.c fwrite_char / fread_char — single pfile owns all
player state.  Python equivalent: mud.db.models.Character (DB row) is the
sole source of truth; mud.account.account_manager writes/reads the DB row
directly.  There is no JSON pfile fallback.

This test verifies that a character saved via mud.account.account_manager
(the production path used by the game loop) round-trips all critical state
correctly through the DB-canonical path.

Invariant (INV-008 reversed): account_manager.save_character /
account_manager.load_character must produce a runtime Character with:
  - character_registry membership (INV-003)
  - correct room placement
  - full gameplay state (level, practice, skills, perm_stat)
  - password_hash round-trip (pcdata.pwd)
  - DB row is the sole canonical source (no JSON fallback)
"""

from __future__ import annotations

import pytest

from mud.account.account_manager import load_character, save_character
from mud.account.account_service import clear_active_accounts, create_character
from mud.db.models import Base
from mud.db.session import engine
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import ROOM_VNUM_SCHOOL
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.security import bans
from mud.world import initialize_world
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
def _clean():
    """Fresh DB for every test — DB-canonical path requires no pfile dir."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    yield


# ---------------------------------------------------------------------------
# INV-008 core: save/load round-trip via account_manager
# ---------------------------------------------------------------------------


def _create_db_char(name: str) -> "Character":
    """Create a character with a DB row, then load it for modification before save.

    Under the DB-canonical path, save_character requires a pre-existing DB row
    (the creation path owns inserts).  This helper calls create_character() to
    insert the row, then load_character() to get a fully-initialized runtime object.
    """
    from mud.account.account_service import create_character
    from mud.db.models import Character as DBCharacter
    from mud.db.session import SessionLocal
    from mud.models.character import from_orm

    create_character(None, name, starting_room_vnum=ROOM_VNUM_SCHOOL)
    # Load fresh from DB for test manipulation
    session = SessionLocal()
    try:
        db_char = session.query(DBCharacter).filter_by(name=name).first()
        assert db_char is not None, f"DB row for {name!r} missing after create_character"
        return from_orm(db_char)
    finally:
        session.close()


def test_inv008_save_load_round_trip_preserves_gameplay_state():
    """INV-008: account_manager save/load must round-trip full gameplay state via DB.

    Save a character with non-default level, practice, and skill values then
    reload and assert all fields survive the DB-canonical round-trip.
    """
    char = _create_db_char("Roundtrip")
    char.level = 5
    char.practice = 12
    char.train = 4
    char.gold = 100
    char.silver = 50
    char.exp = 2500
    char.hitroll = 3
    char.damroll = 2
    char.mana = 80
    char.move = 90
    # max_mana/max_move derive from perm_mana/perm_move on load (ROM handler.c:607-609).
    # Set perm values so max values round-trip correctly via derived restore.
    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.perm_mana = 100
    char.pcdata.perm_move = 120
    char.skills["recall"] = 75

    save_character(char)

    loaded = load_character("Roundtrip")
    assert loaded is not None, "load_character must return a Character after DB save"
    assert loaded.level == 5
    assert loaded.practice == 12
    assert loaded.train == 4
    assert loaded.gold == 100
    assert loaded.silver == 50
    assert loaded.exp == 2500
    assert loaded.hitroll == 3
    assert loaded.damroll == 2
    assert loaded.mana == 80
    assert loaded.max_mana == 100  # derived from perm_mana on load
    assert loaded.move == 90
    assert loaded.max_move == 120  # derived from perm_move on load
    assert loaded.skills.get("recall") == 75


def test_inv008_load_registers_character():
    """INV-008 + INV-003: load_character via account_manager adds to registry."""
    char = _create_db_char("Regtest")
    save_character(char)

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
    """INV-008: pcdata.pwd survives save/load via account_manager DB path."""
    char = _create_db_char("Pwdtest")
    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.pwd = "$argon2id$v=19$m=65536,t=3,p=4$inv008test"

    save_character(char)

    loaded = load_character("Pwdtest")
    assert loaded is not None
    assert loaded.pcdata is not None
    assert loaded.pcdata.pwd == "$argon2id$v=19$m=65536,t=3,p=4$inv008test", (
        "pcdata.pwd must survive account_manager DB save/load (INV-008)"
    )


def test_inv008_room_placement_survives_round_trip():
    """INV-008: room placement persists and loads correctly via DB path."""
    char = _create_db_char("Roomtest")
    save_character(char)

    loaded = load_character("Roomtest")
    assert loaded is not None
    assert loaded.room is not None
    assert loaded.room.vnum == ROOM_VNUM_SCHOOL


def test_inv008_db_canonical_is_sole_path():
    """INV-008 reversed: DB row is the sole canonical source; no JSON fallback exists.

    A character created via create_character() (which inserts the DB row)
    must be loadable via load_character() without any JSON pfile present.
    The DB path is the only path — not a fallback.
    """
    char_name = "Legacyx"
    created = create_character(None, char_name, starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created, "create_character must succeed"

    # No pfile is written — if the JSON path were consulted it would return None
    loaded = load_character(char_name)
    assert loaded is not None, "load_character must find character via DB (sole path)"
    assert loaded.name == char_name
    assert loaded in character_registry, "loaded character must be in character_registry (INV-003)"
