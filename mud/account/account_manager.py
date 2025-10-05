from __future__ import annotations

import json

from mud.db.models import Character as DBCharacter
from mud.db.models import PlayerAccount
from mud.db.session import SessionLocal
from mud.models.character import Character, from_orm
from mud.models.conversion import (
    load_objects_for_character,
    save_objects_for_character,
)


def load_character(username: str, char_name: str) -> Character | None:
    session = None
    try:
        session = SessionLocal()
        db_char = (
            session.query(DBCharacter)
            .join(PlayerAccount)
            .filter(
                DBCharacter.name == char_name,
                PlayerAccount.username == username,
            )
            .first()
        )
        char = from_orm(db_char) if db_char else None
        if char and db_char:
            _ = db_char.player  # load relationship
            char.inventory, char.equipment = load_objects_for_character(db_char)
        return char
    except Exception as e:
        print(f"[ERROR] Failed to load character {char_name}: {e}")
        return None
    finally:
        if session:
            session.close()


def save_character(character: Character) -> None:
    session = None
    try:
        session = SessionLocal()
        db_char = session.query(DBCharacter).filter_by(name=character.name).first()
        if db_char:
            db_char.level = character.level
            db_char.hp = character.hit
            db_char.race = int(character.race or 0)
            db_char.ch_class = int(character.ch_class or 0)
            db_char.sex = int(character.sex or 0)
            db_char.alignment = int(character.alignment or 0)
            db_char.act = int(getattr(character, "act", 0) or 0)
            db_char.hometown_vnum = int(character.hometown_vnum or 0)
            db_char.perm_stats = json.dumps([int(val) for val in character.perm_stat])
            db_char.size = int(character.size or 0)
            db_char.form = int(character.form or 0)
            db_char.parts = int(character.parts or 0)
            db_char.imm_flags = int(character.imm_flags or 0)
            db_char.res_flags = int(character.res_flags or 0)
            db_char.vuln_flags = int(character.vuln_flags or 0)
            db_char.practice = int(character.practice or 0)
            db_char.train = int(character.train or 0)
            db_char.default_weapon_vnum = int(character.default_weapon_vnum or 0)
            db_char.creation_points = int(getattr(character, "creation_points", 0) or 0)
            db_char.creation_groups = json.dumps(list(getattr(character, "creation_groups", ())))
            if getattr(character, "room", None):
                db_char.room_vnum = character.room.vnum
            save_objects_for_character(session, character, db_char)
            session.commit()
    except Exception as e:
        print(f"[ERROR] Failed to save character {character.name}: {e}")
    finally:
        if session:
            session.close()
