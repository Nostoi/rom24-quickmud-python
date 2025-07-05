from __future__ import annotations

from typing import Optional

from mud.db.session import SessionLocal
from mud.db.models import Character as DBCharacter
from mud.models.character import Character, from_orm
from mud.models.conversion import load_objects_for_character, save_objects_for_character


def load_character(username: str, char_name: str) -> Optional[Character]:
    session = SessionLocal()
    db_char = session.query(DBCharacter).filter_by(name=char_name).first()
    char = from_orm(db_char) if db_char else None
    if char:
        char.inventory, char.equipment = load_objects_for_character(db_char)
    session.close()
    return char


def save_character(character: Character) -> None:
    session = SessionLocal()
    db_char = session.query(DBCharacter).filter_by(name=character.name).first()
    if db_char:
        db_char.level = character.level
        db_char.hp = character.hit
        if getattr(character, "room", None):
            db_char.room_vnum = character.room.vnum
        save_objects_for_character(session, character, db_char)
        session.commit()
    session.close()
