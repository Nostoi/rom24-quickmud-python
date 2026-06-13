"""INV-046 (PHANTOM-REGISTRY) family 3b — phantom stat-table aliases.

A second wave of immortal/info commands read attributes that ``mud/registry.py``
never defines — ``skill_table``, ``object_list``, ``areas``, ``rooms``, ``helps``,
``social_table``/``social_registry``, ``player_registry``, ``note_boards``,
``group_table`` — via ``getattr(registry, "<name>", default)``. Unlike family 3a
(``mfind``/``ofind``, which *crashed*), these silently returned the empty default
in production: ``memory`` printed ``Socials 0``, ``owhere`` found nothing,
``slookup`` listed no skills, ``count``'s fallback counted zero, ``socials``
answered "No socials found.", ``groups all`` showed "(no groups defined)".

Each reader is rewired to the real backing structure:

- ``skill_table``   → ``mud.skills.registry.skill_registry.skills`` (name-keyed)
                      and ``char.skills`` for the learned store (sset)
- ``object_list``   → ``mud.models.obj.object_registry`` (live ``Object`` list)
- ``areas``/``rooms`` → ``registry.area_registry`` / ``registry.room_registry``
- ``helps``         → ``mud.models.help.help_entries``
- ``social_table``  → ``mud.models.social.social_registry``
- ``player_registry`` → ``mud.models.character.character_registry`` (PC filter)
- ``note_boards``   → ``mud.notes.board_registry``
- ``group_table``   → ``mud.skills.groups`` (``.skills`` field, not ``.spells``)

The autouse fixture strips every family-3b alias from ``mud.registry`` so these
tests exercise the PRODUCTION shape — if any reader still reads a phantom, it
scans nothing and the assertion fails. See AGENTS.md "Cross-File Invariants",
docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-046, and the Layer-A guard
tests/test_phantom_registry_convention.py.
"""

from __future__ import annotations

import re

import pytest

from mud import registry as global_registry
from mud.commands.imm_search import do_memory, do_owhere, do_slookup
from mud.commands.imm_set import do_sset
from mud.commands.info_extended import do_count, do_whois
from mud.commands.misc_info import do_socials
from mud.commands.misc_player import do_unread
from mud.commands.remaining_rom import do_groups
from mud.models.character import character_registry
from mud.spawning.obj_spawner import spawn_object
from mud.world import create_test_character, initialize_world

ROOM = 3001

_FAMILY_3B_ALIASES = (
    "skill_table",
    "object_list",
    "areas",
    "rooms",
    "helps",
    "social_table",
    "social_registry",
    "player_registry",
    "note_boards",
    "group_table",
    "descriptor_list",
)


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


@pytest.fixture(autouse=True)
def _production_registry_shape():
    """Simulate production: ``mud.registry`` carries none of the phantom aliases."""
    saved = {}
    for attr in _FAMILY_3B_ALIASES:
        if hasattr(global_registry, attr):
            saved[attr] = getattr(global_registry, attr)
            delattr(global_registry, attr)
    yield
    for attr in _FAMILY_3B_ALIASES:
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)
    for attr, value in saved.items():
        setattr(global_registry, attr, value)


def _imm(name: str, room_vnum: int = ROOM):
    char = create_test_character(name, room_vnum)
    char.level = 60
    char.trust = 60
    return char


def _cleanup(*chars) -> None:
    for ch in chars:
        room = getattr(ch, "room", None)
        if room is not None and ch in room.people:
            room.people.remove(ch)
        if ch in character_registry:
            character_registry.remove(ch)


# --- skill_table → skill_registry / char.skills -----------------------------


def test_slookup_finds_skill_via_real_registry():
    # mirrors ROM src/act_wiz.c:3191-3229 — slookup walks skill_table[sn].
    char = _imm("Slooker")
    out = do_slookup(char, "acid blast")
    assert "acid blast" in out
    assert "Sn:" in out and "Slot:" in out
    _cleanup(char)


def test_slookup_all_lists_loaded_skills():
    char = _imm("Slookall")
    out = do_slookup(char, "all")
    # 134 skills load from data/skills.json — a phantom empty list prints nothing.
    assert out.count("Skill/spell:") > 50
    _cleanup(char)


def test_sset_writes_to_char_skills_store():
    # mirrors ROM src/act_wiz.c do_sset — sets the victim's skill percentage.
    # ROM parses the skill as a single one_argument prefix word, so "acid"
    # prefix-matches the loaded skill "acid blast" (skill_lookup str_prefix).
    imm = _imm("Ssetter")
    victim = create_test_character("Ssetvictim", ROOM)
    result = do_sset(imm, "Ssetvictim acid 75")
    # Canonical learned store is char.skills (name-keyed), not pcdata.learned[sn].
    assert victim.skills.get("acid blast") == 75
    assert "No such skill" not in result
    _cleanup(imm, victim)


# --- object_list → object_registry ------------------------------------------


def test_owhere_finds_object_via_object_registry():
    # mirrors ROM src/act_wiz.c:1886-1948 — owhere walks object_list.
    char = _imm("Owherer")
    obj = spawn_object(3010)  # "the donation pit", name "pit"
    assert obj is not None
    out = do_owhere(char, "pit")
    assert "pit" in out.lower()
    assert out != "Nothing like that in heaven or earth."
    _cleanup(char)


# --- areas/rooms/helps/socials → real registries (do_memory) ----------------


def test_memory_counts_are_nonzero():
    # mirrors ROM src/db.c:3289-3330 — memory prints table sizes.
    char = _imm("Memer")
    out = do_memory(char, "")

    def _count(label: str) -> int:
        m = re.search(rf"{label}\s+(\d+)", out)
        assert m, f"{label} line missing from:\n{out}"
        return int(m.group(1))

    assert _count("Areas") > 0
    assert _count("Rooms") > 0
    assert _count("Helps") > 0
    assert _count("Socials") > 0
    _cleanup(char)


# --- player_registry → character_registry (count / whois fallback) ----------


def test_count_fallback_uses_character_registry_pcs():
    # mirrors ROM src/act_info.c:2228-2252 — do_count walks descriptor_list;
    # with no live descriptors the Python fallback counts live PCs.
    a = create_test_character("Counta", ROOM)
    b = create_test_character("Countb", ROOM)
    out = do_count(a, "")
    m = re.search(r"There are (\d+) characters on", out)
    assert m, out
    assert int(m.group(1)) >= 2
    _cleanup(a, b)


def test_whois_fallback_finds_pc_in_character_registry():
    char = _imm("Whoiser")
    target = create_test_character("Whoistarget", ROOM)
    target.level = 10
    out = do_whois(char, "Whoistarget")
    assert "Whoistarget" in out
    assert out != "No one of that name is playing."
    _cleanup(char, target)


# --- note_boards → board_registry -------------------------------------------


def test_unread_reports_note_via_board_registry():
    # mirrors ROM note handling — unread counts notes newer than the per-board
    # last-read stamp. Boards live in mud.notes.board_registry; the read stamp
    # lives in pcdata.last_notes (name → timestamp), NOT the phantom
    # registry.note_boards / pcdata.last_read the old reader used.
    from mud.models.board import Board
    from mud.notes import board_registry

    board = Board(name="inv046test", description="INV-046 family 3b probe")
    board.post(sender="tester", subject="hi", text="body", timestamp=100)
    board_registry["inv046test"] = board
    try:
        char = _imm("Unreader")
        char.pcdata.last_notes = {"inv046test": 0.0}
        out = do_unread(char, "")
        assert "inv046test" in out
        assert out != "There are no note boards."
        assert out != "You have no unread notes."
        _cleanup(char)
    finally:
        board_registry.pop("inv046test", None)


# --- social_table → social_registry -----------------------------------------


def test_socials_lists_from_social_registry():
    # mirrors ROM src/act_info.c:606-625 — do_socials lists the social table.
    char = _imm("Socialer")
    out = do_socials(char, "")
    assert out != "No socials found."
    # 244 socials load from data/socials.json.
    assert "smile" in out.lower() or "grin" in out.lower()
    _cleanup(char)


# --- group_table → mud.skills.groups ----------------------------------------


def test_groups_all_lists_real_groups():
    char = _imm("Grouper")
    out = do_groups(char, "all")
    assert "rom basics" in out
    assert "(no groups defined)" not in out
    _cleanup(char)


def test_groups_named_shows_skills():
    # ROM GroupType exposes .skills (not .spells) — the old reader used the
    # wrong field name and would have shown "(none)".
    char = _imm("Grouperb")
    out = do_groups(char, "rom basics")
    assert "scrolls" in out
    assert "(none)" not in out
    _cleanup(char)
