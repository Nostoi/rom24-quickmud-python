from __future__ import annotations

import json

from mud.db.models import Character as DBCharacter
from mud.db.models import PlayerAccount
from mud.db.session import SessionLocal
from mud.models.character import Character, from_orm
from mud.models.constants import ROOM_VNUM_LIMBO, ROOM_VNUM_TEMPLE
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
        if not db_char:
            # Character doesn't exist in database - create it
            # This handles cases where character was created via JSON or other means
            print(f"[WARN] Character '{character.name}' not found in database, creating new record")
            
            # CRITICAL: Try to find and link the player account
            player_id = None
            pcdata = getattr(character, "pcdata", None)
            if pcdata:
                account_name = getattr(pcdata, "account_name", None)
                if account_name:
                    player_account = session.query(PlayerAccount).filter_by(username=account_name).first()
                    if player_account:
                        player_id = player_account.id
                        print(f"[INFO] Linked character '{character.name}' to account '{account_name}' (id={player_id})")
                    else:
                        print(f"[WARN] Could not find player account '{account_name}' for character '{character.name}'")
            
            db_char = DBCharacter(name=character.name, player_id=player_id)
            session.add(db_char)
        
        # Update all fields
        if db_char:
            # Ensure player_id is set if we have account information
            if not db_char.player_id:
                pcdata = getattr(character, "pcdata", None)
                if pcdata:
                    account_name = getattr(pcdata, "account_name", None)
                    if account_name:
                        player_account = session.query(PlayerAccount).filter_by(username=account_name).first()
                        if player_account:
                            db_char.player_id = player_account.id
                            print(f"[INFO] Fixed missing player_id for character '{character.name}' -> account '{account_name}'")
            
            db_char.level = character.level
            db_char.hp = character.hit
            db_char.race = int(character.race or 0)
            db_char.ch_class = int(character.ch_class or 0)
            pcdata = getattr(character, "pcdata", None)
            true_sex_value = int(getattr(pcdata, "true_sex", getattr(character, "sex", 0)) or 0)
            db_char.true_sex = true_sex_value
            db_char.sex = int(character.sex or true_sex_value or 0)
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

            # Save perm stats from pcdata (ROM src/handler.c stores perm_hit/perm_mana/perm_move)
            if pcdata:
                db_char.perm_hit = int(getattr(pcdata, "perm_hit", character.max_hit or 20))
                db_char.perm_mana = int(getattr(pcdata, "perm_mana", character.max_mana or 100))
                db_char.perm_move = int(getattr(pcdata, "perm_move", character.max_move or 100))
            else:
                # Fallback if no pcdata
                db_char.perm_hit = int(character.max_hit or 20)
                db_char.perm_mana = int(character.max_mana or 100)
                db_char.perm_move = int(character.max_move or 100)

            db_char.default_weapon_vnum = int(character.default_weapon_vnum or 0)
            db_char.creation_points = int(getattr(character, "creation_points", 0) or 0)
            db_char.creation_groups = json.dumps(list(getattr(character, "creation_groups", ())))
            db_char.newbie_help_seen = bool(getattr(character, "newbie_help_seen", False))
            room = getattr(character, "room", None)
            was_in_room = getattr(character, "was_in_room", None)
            room_vnum = 0
            if room is not None:
                room_vnum = int(getattr(room, "vnum", 0) or 0)
                if room_vnum == int(ROOM_VNUM_LIMBO) and was_in_room is not None:
                    room_vnum = int(getattr(was_in_room, "vnum", 0) or 0)
            elif was_in_room is not None:
                room_vnum = int(getattr(was_in_room, "vnum", 0) or 0)
            if room_vnum <= 0:
                room_vnum = int(ROOM_VNUM_TEMPLE)
            db_char.room_vnum = room_vnum
            save_objects_for_character(session, character, db_char)
            session.commit()
    except Exception as e:
        print(f"[ERROR] Failed to save character {character.name}: {e}")
    finally:
        if session:
            session.close()
