"""Account manager — thin shim delegating to mud.persistence (INV-008 hybrid).

The JSON pfile (mud.persistence) is the single source of truth for ALL player
gameplay state.  The DB row (mud.db.models.Character) owns auth only:
  - ``name``   — lookup key
  - ``password_hash`` — bcrypt/argon2 credential

``load_character`` tries the JSON pfile first; if no JSON exists (legacy DB-only
row or freshly-created character not yet saved), it falls back to ``from_orm``
so the caller gets a valid runtime Character rather than None.  The next
``save_character`` call promotes the row to JSON transparently.

``save_character`` writes the JSON pfile via mud.persistence.  It does NOT
update gameplay columns on the DB row — those are vestigial under the hybrid
scheme.  The one exception: when ``pcdata.pwd`` has changed (e.g. do_password),
the new hash is also written to ``db.password_hash`` so the auth path
(account_service.login_character) which reads from the DB continues to work.

ROM Reference: src/save.c fread_char / fwrite_char — the C engine's pfile is
also the single source of truth; the only external auth store is the pfile
itself (``password <hash>`` line).

INV-008: DUAL-LOAD-CHARACTER-COHERENCE — consolidated by this module.
"""

from __future__ import annotations

import mud.persistence as _persistence
from mud.db.models import Character as DBCharacter
from mud.db.session import SessionLocal
from mud.models.character import Character, character_registry, from_orm
from mud.models.conversion import load_objects_for_character


def load_character(char_name: str, _ignored: str | None = None) -> Character | None:
    """Load a character by name — JSON pfile first, DB fallback.

    The second argument is accepted but ignored for backward compatibility;
    previously it was a username (account name).  Characters are standalone
    identities — mirroring ROM src/save.c:fread_char.

    Load order:
    1. JSON pfile (mud.persistence.load_character) — full 51-field state.
    2. DB row (from_orm) — legacy fallback for rows that have no pfile yet
       (e.g. freshly created characters before their first save).

    The loaded character is appended to ``character_registry`` (INV-003).
    mud.persistence.load_character already does this for path 1; path 2
    mirrors it explicitly.
    """
    # Path 1: JSON pfile — canonical full-state load
    char = _persistence.load_character(char_name)
    if char is not None:
        return char

    # Path 2: DB-only fallback (legacy row / freshly created character)
    session = None
    try:
        session = SessionLocal()
        db_char = session.query(DBCharacter).filter(DBCharacter.name == char_name).first()
        if db_char is None:
            return None
        char = from_orm(db_char)
        if char is not None:
            char.inventory, char.equipment = load_objects_for_character(db_char)
            if char not in character_registry:
                character_registry.append(char)
        return char
    except Exception as e:
        print(f"[ERROR] Failed to load character {char_name} from DB: {e}")
        return None
    finally:
        if session:
            session.close()


def save_character(character: Character) -> None:
    """Persist ``character`` to the JSON pfile.

    Also syncs ``password_hash`` to the DB row if ``pcdata.pwd`` is set, so
    the auth path (account_service.login_character) which reads from the DB
    stays consistent after a ``do_password`` call.
    """
    # Primary write: JSON pfile owns all gameplay state
    _persistence.save_character(character)

    # Secondary write: keep DB password_hash in sync with pcdata.pwd
    pcdata = getattr(character, "pcdata", None)
    if not pcdata:
        return
    pwd = getattr(pcdata, "pwd", "") or ""
    if not pwd:
        return

    session = None
    try:
        session = SessionLocal()
        db_char = session.query(DBCharacter).filter_by(name=character.name).first()
        if db_char is not None and getattr(db_char, "password_hash", "") != pwd:
            db_char.password_hash = pwd
            session.commit()
    except Exception as e:
        print(f"[WARN] Failed to sync password_hash to DB for {character.name}: {e}")
    finally:
        if session:
            session.close()
