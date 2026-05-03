"""Unit tests for INV-008: password_hash persists through the JSON pfile round-trip.

ROM parity: ROM src/save.c fwrite_char / fread_char preserves the password hash
(``pwd``) in the pfile so the player's credentials survive logout/login without
touching the auth backend.  This test verifies the Python equivalent:
``mud.persistence.save_character`` writes ``pcdata.pwd`` into the JSON snapshot
and ``mud.persistence.load_character`` restores it to ``pcdata.pwd``.
"""

from __future__ import annotations

import mud.persistence as persistence
from mud.models.character import PCData, character_registry
from mud.world import create_test_character, initialize_world


def test_password_hash_round_trips_through_json(tmp_path):
    """INV-008: save_character writes pcdata.pwd; load_character restores it."""
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")

    char = create_test_character("Pwtest", 3001)
    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.pwd = "$argon2id$v=19$m=65536,t=3,p=4$fakehash"

    persistence.save_character(char)

    loaded = persistence.load_character("Pwtest")
    assert loaded is not None
    assert loaded.pcdata is not None
    assert loaded.pcdata.pwd == "$argon2id$v=19$m=65536,t=3,p=4$fakehash", (
        "pcdata.pwd must survive a save/load round-trip through the JSON pfile"
    )


def test_empty_password_hash_round_trips_safely(tmp_path):
    """INV-008: a character with no password hash loads without error."""
    persistence.PLAYERS_DIR = tmp_path
    character_registry.clear()
    initialize_world("area/area.lst")

    char = create_test_character("Nopwd", 3001)
    if char.pcdata is None:
        char.pcdata = PCData()
    char.pcdata.pwd = ""

    persistence.save_character(char)

    loaded = persistence.load_character("Nopwd")
    assert loaded is not None
    assert loaded.pcdata is not None
    assert loaded.pcdata.pwd == ""
