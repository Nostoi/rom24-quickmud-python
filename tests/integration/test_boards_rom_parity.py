"""ROM ``board.c`` parity tests.

Each test cites the ROM C reference being mirrored. Source of truth is
``src/board.c`` — when a Python behavior diverges, the test asserts ROM
behavior and the implementation is the thing that must change.
"""

from __future__ import annotations

import time

import pytest

import mud.notes as notes
from mud.commands.dispatcher import process_command
from mud.models.board import BoardForceType
from mud.models.character import character_registry
from mud.models.constants import LEVEL_IMMORTAL, MAX_LEVEL
from mud.world import create_test_character, initialize_world


def _setup_boards(tmp_path):
    orig_dir = notes.BOARDS_DIR
    notes.BOARDS_DIR = tmp_path
    notes.board_registry.clear()
    notes._last_note_stamp = 0.0
    return orig_dir


def _teardown_boards(orig_dir):
    notes.board_registry.clear()
    notes._last_note_stamp = 0.0
    notes.BOARDS_DIR = orig_dir


def test_rom_default_boards_seeded_on_load(tmp_path):
    """Mirror ROM ``boards[MAX_BOARD]`` table at ``src/board.c:67-76``.

    BOARD-001: the five hardcoded ROM boards must exist after a fresh
    ``load_boards()`` with their ROM levels / force-types / purge-days /
    default recipients.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        notes.load_boards()

        general = notes.find_board("General")
        ideas = notes.find_board("Ideas")
        announce = notes.find_board("Announce")
        bugs = notes.find_board("Bugs")
        personal = notes.find_board("Personal")

        assert general is not None
        assert ideas is not None
        assert announce is not None
        assert bugs is not None
        assert personal is not None

        # ROM src/board.c:70  General  read=0 write=2 default="all" INCLUDE 21
        assert (general.read_level, general.write_level) == (0, 2)
        assert general.default_recipients == "all"
        assert general.force_type is BoardForceType.INCLUDE
        assert general.purge_days == 21

        # ROM src/board.c:71  Ideas    read=0 write=2 default="all" NORMAL  60
        assert (ideas.read_level, ideas.write_level) == (0, 2)
        assert ideas.force_type is BoardForceType.NORMAL
        assert ideas.purge_days == 60

        # ROM src/board.c:72  Announce read=0 write=L_IMM default="all" NORMAL 60
        assert (announce.read_level, announce.write_level) == (0, LEVEL_IMMORTAL)
        assert announce.force_type is BoardForceType.NORMAL
        assert announce.purge_days == 60

        # ROM src/board.c:73  Bugs     read=0 write=1 default="imm" NORMAL 60
        assert (bugs.read_level, bugs.write_level) == (0, 1)
        assert bugs.default_recipients == "imm"
        assert bugs.force_type is BoardForceType.NORMAL
        assert bugs.purge_days == 60

        # ROM src/board.c:74  Personal read=0 write=1 default="all" EXCLUDE 28
        assert (personal.read_level, personal.write_level) == (0, 1)
        assert personal.default_recipients == "all"
        assert personal.force_type is BoardForceType.EXCLUDE
        assert personal.purge_days == 28
    finally:
        _teardown_boards(orig_dir)


def test_post_assigns_unique_timestamp_when_called_in_same_second(tmp_path):
    """Mirror ROM ``finish_note`` ``last_note_stamp`` logic at ``src/board.c:154-160``.

    BOARD-004: two notes posted in the same second must get distinct,
    monotonically increasing timestamps so the unread cursor cannot collide.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        notes.load_boards()
        board = notes.find_board("General")
        assert board is not None
        board.notes.clear()
        notes._last_note_stamp = 0.0  # reset module-level clock

        fixed = 1_700_000_000
        a = board.post("alice", "subj", "text", to="all", timestamp=fixed)
        b = board.post("alice", "subj", "text", to="all", timestamp=fixed)
        c = board.post("alice", "subj", "text", to="all", timestamp=fixed)

        assert a.timestamp == fixed
        assert b.timestamp > a.timestamp
        assert c.timestamp > b.timestamp
    finally:
        _teardown_boards(orig_dir)


def test_unread_count_skips_notes_not_addressed_to_reader(tmp_path):
    """Mirror ROM ``unread_notes`` recipient filter at ``src/board.c:444-460``.

    BOARD-005: notes whose ``to_list`` does not include the reader must not
    contribute to that reader's unread count.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()

        notes.load_boards()
        personal = notes.find_board("Personal")
        assert personal is not None
        personal.notes.clear()

        bob = create_test_character("Bob", 3001)
        bob.level = 5
        # Note addressed only to Alice — Bob should not see it as unread.
        personal.post("alice", "private", "hi", to="Alice", timestamp=1_700_000_010)

        unread = personal.unread_count_for(bob, last_read=0.0)
        assert unread == 0

        alice = create_test_character("Alice", 3001)
        alice.level = 5
        assert personal.unread_count_for(alice, last_read=0.0) == 1
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_load_boards_archives_expired_notes(tmp_path):
    """Mirror ROM ``load_board`` archive sweep at ``src/board.c:365-383``.

    BOARD-008: a note whose ``expire`` is in the past at load time must be
    removed from the active board and appended to ``<board>.old``.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        notes.load_boards()
        board = notes.find_board("General")
        assert board is not None
        board.notes.clear()

        now = time.time()
        # One expired, one live.
        board.post("alice", "old", "stale", to="all", timestamp=now - 100, expire=now - 50)
        board.post("alice", "fresh", "live", to="all", timestamp=now - 10, expire=now + 60 * 60 * 24)
        notes.save_board(board)

        # Reload — expired note should be dropped and archived.
        notes.board_registry.clear()
        notes.load_boards()
        reloaded = notes.find_board("General")
        assert reloaded is not None
        subjects = [n.subject for n in reloaded.notes]
        assert "old" not in subjects
        assert "fresh" in subjects

        archive_path = tmp_path / f"{reloaded.storage_key()}.old.json"
        assert archive_path.exists(), "expired note must be archived to <board>.old.json"
    finally:
        _teardown_boards(orig_dir)


def test_personal_message_posts_to_personal_board(tmp_path):
    """Mirror ROM ``personal_message`` / ``make_note`` at ``src/board.c:843-886``.

    BOARD-013: a programmatic call must append a note to the Personal board
    with sender/to/subject/text from the call and ``expire = now + days*86400``,
    and must assign a unique monotonic ``date_stamp`` via ``finish_note``.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        notes.load_boards()
        personal = notes.find_board("Personal")
        assert personal is not None
        personal.notes.clear()

        before = time.time()
        note = notes.personal_message(
            sender="System",
            to="Alice",
            subject="Death",
            expire_days=28,
            text="You have died.",
        )
        after = time.time()

        assert note is not None
        # Must land on the Personal board (ROM ``make_note ("Personal", ...)``).
        assert note in personal.notes
        assert note.sender == "System"
        assert note.to == "Alice"
        assert note.subject == "Death"
        assert note.text == "You have died."
        # expire = current_time + expire_days * 60 * 60 * 24 (ROM line 875)
        expected_min = before + 28 * 86400
        expected_max = after + 28 * 86400 + 1
        assert expected_min <= note.expire <= expected_max
    finally:
        _teardown_boards(orig_dir)


def test_make_note_returns_none_for_unknown_board(tmp_path):
    """Mirror ROM ``make_note`` BOARD_NOTFOUND branch at ``src/board.c:855-859``.

    BOARD-013: an unknown board name causes ROM to ``bug`` and return without
    posting. The Python equivalent must return ``None`` and not create a board.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        notes.load_boards()
        before = set(notes.board_registry.keys())
        result = notes.make_note(
            board_name="NoSuchBoard",
            sender="System",
            to="Alice",
            subject="x",
            expire_days=1,
            text="x",
        )
        assert result is None
        # Must not have lazily created a new board for an unknown name.
        assert set(notes.board_registry.keys()) == before
    finally:
        _teardown_boards(orig_dir)


def test_make_note_rejects_text_exceeding_max_note_text(tmp_path):
    """Mirror ROM ``make_note`` length check at ``src/board.c:861-865``.

    BOARD-013: ``MAX_NOTE_TEXT = 4 * MAX_STRING_LENGTH - 1000 = 17432``. Text
    longer than that is rejected (ROM bugs and returns); no note is appended.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        notes.load_boards()
        personal = notes.find_board("Personal")
        assert personal is not None
        personal.notes.clear()

        oversized = "x" * (notes.MAX_NOTE_TEXT + 1)
        result = notes.make_note(
            board_name="Personal",
            sender="System",
            to="Alice",
            subject="overflow",
            expire_days=1,
            text=oversized,
        )
        assert result is None
        assert personal.notes == []
    finally:
        _teardown_boards(orig_dir)


def test_note_write_broadcasts_to_room(tmp_path):
    """Mirror ROM ``do_nwrite`` TO_ROOM ``act`` at ``src/board.c:503``.

    BOARD-002: starting a note emits ``$n starts writing a note.`` to the
    actor's room (excluding the actor).
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        notes.load_boards()

        author = create_test_character("Author", 3001)
        author.level = 5
        bystander = create_test_character("Bystander", 3001)
        bystander.level = 5
        # drain any login broadcast already queued
        bystander.messages.clear()

        process_command(author, "note write")

        joined = "\n".join(bystander.messages)
        assert "starts writing" in joined.lower()
        assert "author" in joined.lower()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_send_broadcasts_to_room(tmp_path):
    """Mirror ROM finish-note TO_ROOM ``act`` at ``src/board.c:1181``.

    BOARD-003: posting (``case 'p':`` in ``handle_con_note_finish``) emits
    ``$n finishes $s note.`` to the actor's room.
    """

    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        notes.load_boards()
        # Switch to the General board so write_level=2 lets level-5 PCs post.
        author = create_test_character("Author", 3001)
        author.level = 5
        process_command(author, "board General")

        bystander = create_test_character("Bystander", 3001)
        bystander.level = 5

        process_command(author, "note write")
        process_command(author, "note subject Hello")
        process_command(author, "note text Greetings, friends.")
        bystander.messages.clear()
        result = process_command(author, "note send")
        assert "posted" in result.lower()

        joined = "\n".join(bystander.messages)
        assert "finishes" in joined.lower()
        assert "note" in joined.lower()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)
