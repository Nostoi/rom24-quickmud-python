"""Account manager — DB-canonical persistence (INV-008 Phase 2).

The DB row (mud.db.models.Character) is the single source of truth for ALL
player gameplay state.  The JSON pfile path (mud.persistence) has been removed.

``save_character`` writes all 71 fields to the DB row via ``save_character_to_db``.
``load_character`` queries the DB row and returns a fully-initialized runtime
Character via ``from_orm``.

ROM Reference: src/save.c fread_char / fwrite_char — the C engine's pfile is
the single source of truth; the only external auth store is the pfile itself.
Python equivalent: the DB row owns both auth and all gameplay state.

INV-003: ``character_registry`` membership is maintained — ``load_character``
appends to the registry after a successful DB load.

INV-008 (DB-CANONICAL): The invariant has been reversed — the DB row is now
the canonical source, not the JSON pfile.  There is no JSON fallback path.
"""

from __future__ import annotations

import time

from mud.db.models import Character as DBCharacter
from mud.db.session import SessionLocal
from mud.models.character import Character, character_registry, from_orm
from mud.models.constants import ROOM_VNUM_LIMBO, ROOM_VNUM_TEMPLE
from mud.persistence import (
    _normalize_int_list,
    _serialize_colour_table,
    _serialize_object,
    _serialize_pet,
    _serialize_skill_map,
    _serialize_groups,
)


def load_character(char_name: str, _ignored: str | None = None) -> Character | None:
    """Load a character by name from the DB row (DB-canonical path).

    The second argument is accepted but ignored for backward compatibility;
    previously it was a username (account name).  Characters are standalone
    identities — mirroring ROM src/save.c:fread_char.

    The loaded character is appended to ``character_registry`` (INV-003).
    """
    session = None
    try:
        session = SessionLocal()
        db_char = session.query(DBCharacter).filter(DBCharacter.name == char_name).first()
        if db_char is None:
            return None
        char = from_orm(db_char)
        if char is not None:
            # Use identity check to avoid triggering dataclass __eq__ on deep
            # object graphs (inventory/equipment items cause recursion with list `in`)
            if not any(c is char for c in character_registry):
                character_registry.append(char)  # INV-003
        return char
    except Exception as e:
        print(f"[ERROR] Failed to load character {char_name} from DB: {e}")
        return None
    finally:
        if session:
            session.close()


def save_character(character: Character) -> None:
    """Persist ``character`` to the DB row (DB-canonical path).

    UPDATE-only: the character row must already exist (created via
    account_service.create_character).  If the row is not found, returns silently.

    ROM Reference: src/save.c fwrite_char — all fields persisted.
    # mirroring mud/persistence.py:save_character (now removed for JSON path)
    """
    session = None
    try:
        session = SessionLocal()
        save_character_to_db(session, character)
        session.commit()
    except Exception as e:
        print(f"[ERROR] save_character failed for {character.name}: {e}")
    finally:
        if session:
            session.close()


def save_character_to_db(session: object, character: Character) -> None:
    """Write all character state to the DB row — the canonical DB save path.

    UPDATE-only: the character row must already exist (created via
    account_service.create_character).  If the row is not found, returns silently.

    Replicates the nontrivial logic from the former mud.persistence.save_character:
      - room_vnum LIMBO → TEMPLE fallback (mirroring ROM src/save.c:fwrite_char)
      - played accumulation: base_played + (now - logon) (ROM src/save.c:fwrite_char)
      - act flags reconciled with ansi_enabled (PlayerFlag.COLOUR bit)
      - All 71 fields from INV008_REVERSAL_AUDIT §1

    Does NOT commit the session — caller is responsible for session.commit()
    so multiple saves can be batched.

    ROM Reference: src/save.c fwrite_char / fwrite_pet
    # mirroring mud/persistence.py:save_character
    """
    from mud.models.constants import PlayerFlag
    from mud.notes import DEFAULT_BOARD_NAME

    db_char = session.query(DBCharacter).filter_by(name=character.name).first()  # type: ignore[union-attr]
    if db_char is None:
        return  # Character must exist — creation path handles inserts

    pcdata = character.pcdata or __import__("mud.models.character", fromlist=["PCData"]).PCData()

    # --- room_vnum: LIMBO fallback → TEMPLE (mirroring persistence.py:913-932) ---
    room = getattr(character, "room", None)
    current_vnum = getattr(room, "vnum", None)
    if current_vnum == ROOM_VNUM_LIMBO:
        was_in_room = getattr(character, "was_in_room", None)
        fallback_vnum = getattr(was_in_room, "vnum", None)
        if fallback_vnum is not None:
            try:
                room_vnum = int(fallback_vnum)
            except (TypeError, ValueError):
                room_vnum = ROOM_VNUM_TEMPLE
        else:
            room_vnum = ROOM_VNUM_TEMPLE
    elif current_vnum is None:
        room_vnum = ROOM_VNUM_TEMPLE
    else:
        try:
            room_vnum = int(current_vnum)
        except (TypeError, ValueError):
            room_vnum = ROOM_VNUM_TEMPLE

    # --- played accumulation (mirroring persistence.py:935-946) ---
    now = int(time.time())
    try:
        logon_value = int(getattr(character, "logon", 0) or 0)
    except (TypeError, ValueError):
        logon_value = 0
    try:
        base_played = int(getattr(character, "played", 0) or 0)
    except (TypeError, ValueError):
        base_played = 0
    session_played = max(0, now - logon_value) if logon_value else 0
    total_played = max(0, base_played + session_played)

    # --- act flags: reconcile ANSI colour bit (mirroring persistence.py:903-911) ---
    ansi_enabled = bool(getattr(character, "ansi_enabled", True))
    act_flags = int(getattr(character, "act", 0))
    colour_bit = int(PlayerFlag.COLOUR)
    if ansi_enabled:
        act_flags |= colour_bit
    else:
        act_flags &= ~colour_bit

    # --- scalar fields ---
    db_char.level = character.level
    db_char.hp = character.hit  # column is named hp, field is hit
    db_char.max_hit = character.max_hit
    db_char.mana = character.mana
    db_char.move = character.move
    db_char.room_vnum = room_vnum
    db_char.race = int(getattr(character, "race", 0))
    db_char.ch_class = int(getattr(character, "ch_class", 0))
    db_char.sex = int(getattr(character, "sex", 0))
    db_char.true_sex = int(getattr(pcdata, "true_sex", 0))
    db_char.alignment = int(getattr(character, "alignment", 0))
    db_char.act = act_flags
    db_char.practice = int(getattr(character, "practice", 0))
    db_char.train = int(getattr(character, "train", 0))
    db_char.perm_hit = int(getattr(pcdata, "perm_hit", 0))
    db_char.perm_mana = int(getattr(pcdata, "perm_mana", 0))
    db_char.perm_move = int(getattr(pcdata, "perm_move", 0))
    db_char.gold = int(getattr(character, "gold", 0))
    db_char.silver = int(getattr(character, "silver", 0))
    db_char.exp = int(getattr(character, "exp", 0))
    db_char.trust = int(getattr(character, "trust", 0))
    db_char.invis_level = int(getattr(character, "invis_level", 0))
    db_char.incog_level = int(getattr(character, "incog_level", 0))
    db_char.saving_throw = int(getattr(character, "saving_throw", 0))
    db_char.hitroll = int(getattr(character, "hitroll", 0))
    db_char.damroll = int(getattr(character, "damroll", 0))
    db_char.wimpy = int(getattr(character, "wimpy", 0))
    db_char.position = int(getattr(character, "position", 8))
    db_char.played = total_played
    db_char.logon = logon_value
    db_char.lines = int(getattr(character, "lines", 22))
    db_char.prompt = getattr(character, "prompt", None)
    prefix_value = getattr(character, "prefix", None)
    db_char.prefix = str(prefix_value) if prefix_value is not None else None
    db_char.affected_by = int(getattr(character, "affected_by", 0))
    db_char.comm = int(getattr(character, "comm", 0))
    db_char.wiznet = int(getattr(character, "wiznet", 0))
    db_char.log_commands = bool(getattr(character, "log_commands", False))
    db_char.newbie_help_seen = bool(getattr(character, "newbie_help_seen", False))
    db_char.pfile_version = 1  # TABLES-001: always ROM-canonical on DB path

    # --- pcdata scalar fields ---
    db_char.title = getattr(pcdata, "title", None)
    bamfin = getattr(pcdata, "bamfin", None)
    db_char.bamfin = str(bamfin) if bamfin is not None else None
    bamfout = getattr(pcdata, "bamfout", None)
    db_char.bamfout = str(bamfout) if bamfout is not None else None
    db_char.security = int(getattr(pcdata, "security", 0))
    db_char.points = int(getattr(pcdata, "points", 0))
    db_char.last_level = int(getattr(pcdata, "last_level", 0))

    # --- password_hash sync ---
    pwd = getattr(pcdata, "pwd", "") or ""
    if pwd:
        db_char.password_hash = pwd

    # --- JSON collection fields ---
    # skills: merge char.skills and pcdata.learned (mirroring persistence.py:898-901)
    skills_snapshot = _serialize_skill_map(getattr(character, "skills", {}))
    pcdata.learned = dict(skills_snapshot)
    db_char.skills = skills_snapshot

    # groups: from pcdata.group_known (mirroring persistence.py:899)
    groups_snapshot = _serialize_groups(getattr(pcdata, "group_known", ()))
    pcdata.group_known = tuple(groups_snapshot)
    db_char.groups = groups_snapshot

    # colours
    colour_table = _serialize_colour_table(pcdata)
    db_char.colours = colour_table

    # conditions [drunk, full, thirst, hunger]
    raw_conditions = list(getattr(pcdata, "condition", []))
    conditions = [0, 48, 48, 48]
    for idx, val in enumerate(raw_conditions[:4]):
        try:
            conditions[idx] = int(val)
        except (TypeError, ValueError):
            pass
    db_char.conditions = conditions

    # armor and mod_stat
    db_char.armor = _normalize_int_list(getattr(character, "armor", []), 4)
    db_char.mod_stat = _normalize_int_list(getattr(character, "mod_stat", []), 5)

    # aliases
    db_char.aliases = dict(getattr(character, "aliases", {}))

    # board name
    board_name = getattr(pcdata, "board_name", DEFAULT_BOARD_NAME) or DEFAULT_BOARD_NAME
    db_char.board = board_name

    # last_notes
    db_char.last_notes = dict(getattr(pcdata, "last_notes", {}) or {})

    # perm_stats JSON (already stored as string, keep existing column)
    from mud.models.character import _encode_perm_stats
    db_char.perm_stats = _encode_perm_stats(getattr(character, "perm_stat", []))

    # creation_groups / creation_skills (keep in sync)
    from mud.models.character import _encode_creation_groups, _encode_creation_skills
    db_char.creation_groups = _encode_creation_groups(getattr(character, "creation_groups", ()))
    db_char.creation_skills = _encode_creation_skills(getattr(character, "creation_skills", ()))
    db_char.creation_points = int(getattr(character, "creation_points", 0) or 0)

    # inventory as JSON blob (Option A from audit §3.1)
    inventory_list = []
    for obj in character.inventory:
        try:
            obj_save = _serialize_object(obj)
            # Convert dataclass to dict for JSON storage
            inventory_list.append(_dataclass_to_dict(obj_save))
        except Exception:
            pass
    db_char.inventory_state = inventory_list

    # equipment as JSON blob (Option A from audit §3.1)
    equipment_dict = {}
    for slot, obj in character.equipment.items():
        try:
            obj_save = _serialize_object(obj, wear_slot=slot)
            equipment_dict[slot] = _dataclass_to_dict(obj_save)
        except Exception:
            pass
    db_char.equipment_state = equipment_dict

    # pet as JSON blob (audit §3.1)
    pet = getattr(character, "pet", None)
    if pet is not None:
        try:
            pet_save = _serialize_pet(pet)
            if pet_save is not None:
                db_char.pet_state = _dataclass_to_dict(pet_save)
            else:
                db_char.pet_state = None
        except Exception:
            db_char.pet_state = None
    else:
        db_char.pet_state = None


def _dataclass_to_dict(obj: object) -> dict:
    """Recursively convert a dataclass instance to a plain dict for JSON storage."""
    import dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for f in dataclasses.fields(obj):  # type: ignore[arg-type]
            val = getattr(obj, f.name)
            if dataclasses.is_dataclass(val) and not isinstance(val, type):
                result[f.name] = _dataclass_to_dict(val)
            elif isinstance(val, list):
                result[f.name] = [
                    _dataclass_to_dict(item) if (dataclasses.is_dataclass(item) and not isinstance(item, type)) else item
                    for item in val
                ]
            elif isinstance(val, dict):
                result[f.name] = {
                    k: (_dataclass_to_dict(v) if (dataclasses.is_dataclass(v) and not isinstance(v, type)) else v)
                    for k, v in val.items()
                }
            else:
                result[f.name] = val
        return result
    return obj  # type: ignore[return-value]
