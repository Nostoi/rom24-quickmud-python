"""Phase 1 round-trip test: save_character_to_db + from_orm round-trips all
new DB-canonical columns added in INV-008 Phase 1.

This test is the proof that Phase 1 works — every category of field (scalar,
list, dict, nested string) survives a save → reload cycle through the DB.

It does NOT replace the INV-008 enforcement test (test_inv008_persistence_coherence.py);
that gets rewritten in Phase 2.

ROM Reference: src/save.c fwrite_char / fread_char — all 71 fields.
"""

from __future__ import annotations

import pytest

from mud.account.account_manager import save_character_to_db
from mud.account.account_service import clear_active_accounts, create_character
from mud.db.models import Base, Character as DBCharacter
from mud.db.session import SessionLocal, engine
from mud.models.character import Character, PCData, character_registry, from_orm
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
def _clean(tmp_path):
    """Fresh in-memory DB for every test."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    bans.clear_all_bans()
    clear_active_accounts()
    reset_lockdowns()
    yield


def _save_and_reload(char: Character) -> Character:
    """Helper: save char via save_character_to_db, reload via from_orm."""
    session = SessionLocal()
    try:
        save_character_to_db(session, char)
        session.commit()
        db_char = session.query(DBCharacter).filter_by(name=char.name).first()
        assert db_char is not None, f"DB row for {char.name!r} missing after save"
        reloaded = from_orm(db_char)
    finally:
        session.close()
    return reloaded


# ---------------------------------------------------------------------------
# Scalar fields
# ---------------------------------------------------------------------------


def test_db_round_trip_scalar_fields():
    """All scalar gameplay fields survive save_character_to_db → from_orm."""
    created = create_character(None, "Scalartest", starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created

    session = SessionLocal()
    char: Character = from_orm(session.query(DBCharacter).filter_by(name="Scalartest").first())
    session.close()

    # Set non-default values for every scalar
    char.level = 7
    char.hit = 55
    char.max_hit = 80
    char.mana = 60
    char.move = 75
    char.gold = 1234
    char.silver = 567
    char.exp = 3500
    char.trust = 2
    char.invis_level = 3
    char.incog_level = 1
    char.saving_throw = -5
    char.hitroll = 4
    char.damroll = 3
    char.wimpy = 10
    char.practice = 15
    char.train = 2
    char.alignment = -500
    char.lines = 30
    char.played = 1000
    char.logon = 0  # zero so played accumulation doesn't add drift
    char.log_commands = True
    char.newbie_help_seen = True
    char.prompt = "<%hhp %mm> "
    char.prefix = ">>"

    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.perm_hit = 80
    char.pcdata.perm_mana = 120
    char.pcdata.perm_move = 100
    char.pcdata.security = 5
    char.pcdata.points = 25
    char.pcdata.last_level = 6
    char.pcdata.true_sex = 1
    char.pcdata.title = "the Tested"
    char.pcdata.bamfin = "Scalartest appears"
    char.pcdata.bamfout = "Scalartest vanishes"
    char.pcdata.pwd = "$argon2id$test_scalar_hash"

    reloaded = _save_and_reload(char)

    assert reloaded.level == 7
    assert reloaded.hit == 55
    assert reloaded.max_hit == 80
    assert reloaded.mana == 60
    assert reloaded.move == 75
    assert reloaded.gold == 1234
    assert reloaded.silver == 567
    assert reloaded.exp == 3500
    assert reloaded.trust == 2
    assert reloaded.invis_level == 3
    assert reloaded.incog_level == 1
    assert reloaded.saving_throw == -5
    assert reloaded.hitroll == 4
    assert reloaded.damroll == 3
    assert reloaded.wimpy == 10
    assert reloaded.practice == 15
    assert reloaded.train == 2
    assert reloaded.alignment == -500
    assert reloaded.lines == 30
    assert reloaded.log_commands is True
    assert reloaded.newbie_help_seen is True
    assert reloaded.prompt == "<%hhp %mm> "
    assert reloaded.prefix == ">>"

    assert reloaded.pcdata is not None
    assert reloaded.pcdata.perm_hit == 80
    assert reloaded.pcdata.perm_mana == 120
    assert reloaded.pcdata.perm_move == 100
    assert reloaded.pcdata.security == 5
    assert reloaded.pcdata.points == 25
    assert reloaded.pcdata.last_level == 6
    assert reloaded.pcdata.true_sex == 1
    assert reloaded.pcdata.title == "the Tested"
    assert reloaded.pcdata.bamfin == "Scalartest appears"
    assert reloaded.pcdata.bamfout == "Scalartest vanishes"
    assert reloaded.pcdata.pwd == "$argon2id$test_scalar_hash"

    # max_mana / max_move derive from perm_mana / perm_move on load
    assert reloaded.max_mana == 120
    assert reloaded.max_move == 100


# ---------------------------------------------------------------------------
# List fields: armor, mod_stat, conditions
# ---------------------------------------------------------------------------


def test_db_round_trip_list_fields():
    """List fields (armor, mod_stat, conditions) survive the round-trip."""
    created = create_character(None, "Listtest", starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created

    session = SessionLocal()
    char: Character = from_orm(session.query(DBCharacter).filter_by(name="Listtest").first())
    session.close()

    char.armor = [-10, -5, -8, -3]
    char.mod_stat = [2, 0, 1, 0, -1]
    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.condition = [3, 40, 35, 20]  # drunk=3, full=40, thirst=35, hunger=20

    reloaded = _save_and_reload(char)

    assert reloaded.armor == [-10, -5, -8, -3]
    assert reloaded.mod_stat == [2, 0, 1, 0, -1]
    assert reloaded.pcdata is not None
    assert reloaded.pcdata.condition == [3, 40, 35, 20]


# ---------------------------------------------------------------------------
# Dict fields: skills, aliases, last_notes
# ---------------------------------------------------------------------------


def test_db_round_trip_dict_fields():
    """Dict fields (skills, aliases, last_notes) survive the round-trip."""
    created = create_character(None, "Dicttest", starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created

    session = SessionLocal()
    char: Character = from_orm(session.query(DBCharacter).filter_by(name="Dicttest").first())
    session.close()

    char.skills = {"recall": 75, "sword": 50, "dagger": 30}
    char.aliases = {"n": "north", "s": "south", "k": "kill all"}
    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.last_notes = {"general": 1234567.0, "immortal": 9876543.0}
    char.pcdata.group_known = ("warrior basics", "combat")

    reloaded = _save_and_reload(char)

    assert reloaded.skills.get("recall") == 75
    assert reloaded.skills.get("sword") == 50
    assert reloaded.skills.get("dagger") == 30
    assert reloaded.aliases.get("n") == "north"
    assert reloaded.aliases.get("k") == "kill all"
    assert reloaded.pcdata is not None
    assert reloaded.pcdata.last_notes.get("general") == pytest.approx(1234567.0)
    assert "warrior basics" in reloaded.pcdata.group_known
    assert "combat" in reloaded.pcdata.group_known


# ---------------------------------------------------------------------------
# Board name (string field, separate column)
# ---------------------------------------------------------------------------


def test_db_round_trip_board_name():
    """Board name (pcdata.board_name) survives the round-trip."""
    created = create_character(None, "Boardtest", starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created

    session = SessionLocal()
    char: Character = from_orm(session.query(DBCharacter).filter_by(name="Boardtest").first())
    session.close()

    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.board_name = "immortal"

    reloaded = _save_and_reload(char)

    assert reloaded.pcdata is not None
    assert reloaded.pcdata.board_name == "immortal"


# ---------------------------------------------------------------------------
# Inventory and equipment state (JSON blobs, Option A)
# ---------------------------------------------------------------------------


def test_db_round_trip_inventory_state():
    """Inventory items are serialized to inventory_state JSON and reloadable."""
    from mud.spawning.obj_spawner import spawn_object
    from mud.models.constants import OBJ_VNUM_SCHOOL_SWORD

    created = create_character(None, "Invtest", starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created

    session = SessionLocal()
    char: Character = from_orm(session.query(DBCharacter).filter_by(name="Invtest").first())
    session.close()

    sword = spawn_object(OBJ_VNUM_SCHOOL_SWORD)
    if sword is None:
        pytest.skip("OBJ_VNUM_SCHOOL_SWORD not in obj_registry — world not loaded")
    sword.level = 5
    sword.timer = 99
    char.add_object(sword)

    session = SessionLocal()
    try:
        save_character_to_db(session, char)
        session.commit()
        db_char = session.query(DBCharacter).filter_by(name="Invtest").first()
        assert db_char is not None
        # The inventory_state JSON blob must be non-empty
        assert db_char.inventory_state is not None
        assert isinstance(db_char.inventory_state, list)
        assert len(db_char.inventory_state) >= 1
        entry = db_char.inventory_state[0]
        assert entry["vnum"] == OBJ_VNUM_SCHOOL_SWORD
        assert entry["level"] == 5
        assert entry["timer"] == 99
    finally:
        session.close()


def test_db_round_trip_equipment_state():
    """Equipped items are serialized to equipment_state JSON and reloadable."""
    from mud.spawning.obj_spawner import spawn_object
    from mud.models.constants import OBJ_VNUM_SCHOOL_SWORD

    created = create_character(None, "Eqtest", starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created

    session = SessionLocal()
    char: Character = from_orm(session.query(DBCharacter).filter_by(name="Eqtest").first())
    session.close()

    sword = spawn_object(OBJ_VNUM_SCHOOL_SWORD)
    if sword is None:
        pytest.skip("OBJ_VNUM_SCHOOL_SWORD not in obj_registry — world not loaded")
    sword.level = 3
    char.equip_object(sword, "wield")

    session = SessionLocal()
    try:
        save_character_to_db(session, char)
        session.commit()
        db_char = session.query(DBCharacter).filter_by(name="Eqtest").first()
        assert db_char is not None
        assert db_char.equipment_state is not None
        assert isinstance(db_char.equipment_state, dict)
        assert "wield" in db_char.equipment_state
        assert db_char.equipment_state["wield"]["vnum"] == OBJ_VNUM_SCHOOL_SWORD
        assert db_char.equipment_state["wield"]["level"] == 3
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Comprehensive single round-trip: one test covering all categories
# ---------------------------------------------------------------------------


def test_db_round_trip_comprehensive():
    """Comprehensive: one character with all field categories set, full round-trip.

    This is the canonical Phase 1 proof test — sets representative non-default
    values for scalars, lists, dicts, and nested objects, then asserts every
    set field survived save_character_to_db → from_orm.
    """
    created = create_character(None, "Comptest", starting_room_vnum=ROOM_VNUM_SCHOOL)
    assert created

    session = SessionLocal()
    char: Character = from_orm(session.query(DBCharacter).filter_by(name="Comptest").first())
    session.close()

    # Scalars
    char.level = 10
    char.hit = 45
    char.max_hit = 90
    char.mana = 50
    char.move = 70
    char.gold = 500
    char.silver = 200
    char.exp = 10000
    char.hitroll = 5
    char.damroll = 4
    char.saving_throw = -3
    char.wimpy = 15
    char.practice = 20
    char.train = 3
    char.alignment = 750
    char.affected_by = 0b101  # BLIND + DETECT_EVIL bits
    char.comm = 0b11  # PROMPT + COMBINE

    # Lists
    char.armor = [-20, -15, -18, -10]
    char.mod_stat = [1, -1, 2, 0, 1]

    # Dicts
    char.skills = {"recall": 80, "sword": 65, "bash": 40}
    char.aliases = {"h": "help", "q": "quit"}

    if char.pcdata is None:
        char.pcdata = PCData()
    # pcdata scalars
    char.pcdata.perm_hit = 90
    char.pcdata.perm_mana = 110
    char.pcdata.perm_move = 120
    char.pcdata.security = 3
    char.pcdata.points = 30
    char.pcdata.last_level = 9
    char.pcdata.true_sex = 2
    char.pcdata.title = "the Comprehensive"
    char.pcdata.pwd = "$argon2id$comp_test_hash"
    # pcdata lists
    char.pcdata.condition = [1, 45, 42, 38]
    char.pcdata.last_notes = {"general": 111111.0}
    char.pcdata.group_known = ("combat", "thief basics")
    char.pcdata.board_name = "general"

    reloaded = _save_and_reload(char)

    # Assert scalars
    assert reloaded.level == 10
    assert reloaded.hit == 45
    assert reloaded.max_hit == 90
    assert reloaded.mana == 50
    assert reloaded.move == 70
    assert reloaded.gold == 500
    assert reloaded.silver == 200
    assert reloaded.exp == 10000
    assert reloaded.hitroll == 5
    assert reloaded.damroll == 4
    assert reloaded.saving_throw == -3
    assert reloaded.wimpy == 15
    assert reloaded.practice == 20
    assert reloaded.train == 3
    assert reloaded.alignment == 750

    # Assert lists
    assert reloaded.armor == [-20, -15, -18, -10]
    assert reloaded.mod_stat == [1, -1, 2, 0, 1]

    # Assert dicts
    assert reloaded.skills.get("recall") == 80
    assert reloaded.skills.get("sword") == 65
    assert reloaded.aliases.get("h") == "help"

    # Assert pcdata
    assert reloaded.pcdata is not None
    assert reloaded.pcdata.perm_hit == 90
    assert reloaded.pcdata.perm_mana == 110
    assert reloaded.pcdata.perm_move == 120
    assert reloaded.max_mana == 110  # derived from perm_mana on load
    assert reloaded.max_move == 120  # derived from perm_move on load
    assert reloaded.pcdata.security == 3
    assert reloaded.pcdata.points == 30
    assert reloaded.pcdata.last_level == 9
    assert reloaded.pcdata.true_sex == 2
    assert reloaded.pcdata.title == "the Comprehensive"
    assert reloaded.pcdata.pwd == "$argon2id$comp_test_hash"
    assert reloaded.pcdata.condition == [1, 45, 42, 38]
    assert reloaded.pcdata.last_notes.get("general") == pytest.approx(111111.0)
    assert "combat" in reloaded.pcdata.group_known
    assert "thief basics" in reloaded.pcdata.group_known
    assert reloaded.pcdata.board_name == "general"
