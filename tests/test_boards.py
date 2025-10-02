import time

import pytest

import mud.notes as notes
from mud import persistence
from mud.commands.dispatcher import process_command
from mud.models.board import BoardForceType
from mud.models.character import character_registry
from mud.models.constants import MAX_LEVEL
from mud.world import create_test_character, initialize_world


def _setup_boards(tmp_path):
    orig_dir = notes.BOARDS_DIR
    notes.BOARDS_DIR = tmp_path
    notes.board_registry.clear()
    return orig_dir


def _teardown_boards(orig_dir):
    notes.board_registry.clear()
    notes.BOARDS_DIR = orig_dir


def test_note_persistence(tmp_path):
    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        char = create_test_character("Author", 3001)
        char.level = 5
        output = process_command(char, "note post Hello|This is a test")
        assert "posted" in output.lower()
        list_output = process_command(char, "note list")
        assert "hello" in list_output.lower()
        assert char.pcdata is not None
        assert char.pcdata.last_notes.get("general", 0) > 0
        notes.board_registry.clear()
        notes.load_boards()
        list_output2 = process_command(char, "note list")
        assert "hello" in list_output2.lower()
        board = notes.find_board("general")
        assert board is not None
        assert board.notes
        assert board.notes[0].expire >= board.notes[0].timestamp
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_initialize_world_loads_boards_from_disk(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        # Seed an existing board file before boot, mirroring ROM boot_db load order.
        board = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        board.post("Immortal", "Welcome", "Follow the rules")
        notes.save_board(board)
        notes.board_registry.clear()

        initialize_world("area/area.lst")
        character_registry.clear()

        loaded_board = notes.find_board("general")
        assert loaded_board is not None
        assert loaded_board.description == "General discussion"

        char = create_test_character("Reader", 3001)
        char.level = 5
        board_output = process_command(char, "board")
        assert "general" in board_output.lower()
        assert "[  1]" in board_output
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_board_switching_and_unread_counts(tmp_path):
    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        general = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        ideas = notes.get_board(
            "Ideas",
            description="Suggestions",
            read_level=0,
            write_level=0,
        )
        personal = notes.get_board(
            "Personal",
            description="Personal messages",
            read_level=60,
            write_level=60,
        )
        general.post("Immortal", "Welcome", "Read the rules")
        notes.save_board(general)

        char = create_test_character("Reader", 3001)
        char.level = 10
        board_output = process_command(char, "board")
        assert "general" in board_output.lower()
        assert "[  1]" in board_output
        assert "[  0]" in board_output
        change_output = process_command(char, "board 2")
        assert "ideas" in change_output.lower()
        assert char.pcdata.board_name == ideas.storage_key()
        deny_output = process_command(char, "board personal")
        assert deny_output == "No such board."
        assert char.pcdata.board_name == ideas.storage_key()
        char.trust = 60
        allow_output = process_command(char, "board personal")
        assert "personal" in allow_output.lower()
        assert char.pcdata.board_name == personal.storage_key()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_board_switching_persists_last_note(tmp_path):
    boards_dir = tmp_path / "boards"
    players_dir = tmp_path / "players"
    orig_board_dir = _setup_boards(boards_dir)
    orig_players = persistence.PLAYERS_DIR
    persistence.PLAYERS_DIR = players_dir
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        general = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        ideas = notes.get_board(
            "Ideas",
            description="Suggestions",
            read_level=0,
            write_level=0,
        )
        char = create_test_character("Archivist", 3001)
        char.level = 50
        char.trust = 50

        post_output = process_command(char, "note post Hello|First note")
        assert "posted" in post_output.lower()
        switch_output = process_command(char, "board ideas")
        assert "ideas" in switch_output.lower()
        assert char.pcdata.board_name == ideas.storage_key()

        persistence.save_character(char)

        general.post("Immortal", "Update", "New policies", timestamp=time.time() + 1)
        notes.save_board(general)
        notes.save_board(ideas)

        notes.board_registry.clear()
        notes.load_boards()
        character_registry.clear()

        loaded = persistence.load_character("Archivist")
        assert loaded is not None
        assert loaded.pcdata.board_name == ideas.storage_key()
        board_listing = process_command(loaded, "board")
        assert "ideas" in board_listing.lower()
        assert "[  1]" in board_listing
    finally:
        character_registry.clear()
        _teardown_boards(orig_board_dir)
        persistence.PLAYERS_DIR = orig_players


def test_board_listing_retains_current_board_without_access(tmp_path):
    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        general = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        personal = notes.get_board(
            "Personal",
            description="Personal messages",
            read_level=60,
            write_level=60,
        )
        notes.save_board(general)
        notes.save_board(personal)

        char = create_test_character("Scout", 3001)
        char.level = 30
        char.trust = 30
        char.pcdata.board_name = personal.storage_key()

        output = process_command(char, "board")
        assert "personal" in output.lower()
        assert "cannot read or write" in output.lower()
        assert char.pcdata.board_name == personal.storage_key()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_board_listing_falls_back_to_default_when_missing(tmp_path):
    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        general = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        notes.save_board(general)

        char = create_test_character("Traveler", 3001)
        char.level = 10
        char.pcdata.board_name = "ghost"

        output = process_command(char, "board")
        assert "general" in output.lower()
        assert char.pcdata.board_name == general.storage_key()
        assert notes.find_board("ghost") is None
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_write_pipeline_enforces_defaults(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        board = notes.get_board(
            "Immortal",
            description="Immortal discussions",
            read_level=0,
            write_level=0,
            default_recipients="imm",
            force_type=BoardForceType.INCLUDE,
            purge_days=14,
        )
        notes.save_board(board)

        char = create_test_character("Scribe", 3001)
        char.level = 60
        char.trust = 60

        process_command(char, "board immortal")

        start_output = process_command(char, "note write")
        assert "immortal" in start_output.lower()
        assert "must include imm" in start_output.lower()

        set_to = process_command(char, "note to mortal")
        assert "mortal imm" in char.pcdata.in_progress.to.lower()
        assert "mortal imm" in set_to.lower()

        subject_output = process_command(char, "note subject Policy Update")
        assert "policy update" in subject_output.lower()

        text_output = process_command(char, "note text Follow the law.")
        assert "updated" in text_output.lower()

        send_output = process_command(char, "note send")
        assert "posted" in send_output.lower()
        assert board.notes[-1].to.lower() == "mortal imm"
        expire_expected = board.notes[-1].timestamp + board.purge_days * 24 * 60 * 60
        assert board.notes[-1].expire == pytest.approx(expire_expected)
        assert char.pcdata.in_progress is None
        assert char.pcdata.last_notes[board.storage_key()] == board.notes[-1].timestamp
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_remove_requires_author_or_immortal(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        board = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        board.post("Scribe", "Hello", "Testing removal", timestamp=time.time())
        board.post("Immortal", "Rules", "Read carefully", timestamp=time.time() + 1)
        notes.save_board(board)

        visitor = create_test_character("Visitor", 3001)
        visitor.level = 30
        visitor.trust = 30

        deny_output = process_command(visitor, "note remove 1")
        assert deny_output == "You are not authorized to remove this note."
        assert len(board.notes) == 2

        author = create_test_character("Scribe", 3001)
        author.level = 40
        author.trust = 40

        author_output = process_command(author, "note remove 1")
        assert author_output == "Note removed!"
        assert len(board.notes) == 1
        assert board.notes[0].subject == "Rules"

        implementor = create_test_character("Implementor", 3001)
        implementor.level = MAX_LEVEL
        implementor.trust = MAX_LEVEL

        imm_output = process_command(implementor, "note remove 1")
        assert imm_output == "Note removed!"
        assert not board.notes
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_remove_rejects_notes_not_addressed_to_character(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        board = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        board.post("Implementor", "Staff", "Immortal briefing", to="imm")
        notes.save_board(board)

        mortal = create_test_character("Adventurer", 3001)
        mortal.level = 30
        mortal.trust = 30

        mortal_output = process_command(mortal, "note remove 1")
        assert mortal_output == "No such note."
        assert len(board.notes) == 1

        implementor = create_test_character("Implementor", 3002)
        implementor.level = MAX_LEVEL
        implementor.trust = MAX_LEVEL

        imm_output = process_command(implementor, "note remove 1")
        assert imm_output == "Note removed!"
        assert not board.notes
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_read_respects_visibility(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        board = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        board.post("Implementor", "Staff", "Immortal briefing", to="imm")
        visible = board.post("Scribe", "News", "Public update")
        notes.save_board(board)

        mortal = create_test_character("Adventurer", 3001)
        mortal.level = 30
        mortal.trust = 30

        hidden_output = process_command(mortal, "note read 1")
        assert hidden_output == "No such note."

        auto_output = process_command(mortal, "note")
        assert "News" in auto_output
        assert "Staff" not in auto_output

        explicit_output = process_command(mortal, "note read 2")
        assert "News" in explicit_output
        assert mortal.pcdata.last_notes[board.storage_key()] == visible.timestamp
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_catchup_marks_all_read(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        board = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        first = board.post("Immortal", "Welcome", "Read the rules", timestamp=time.time())
        second = board.post(
            "Immortal",
            "Changes",
            "Policy update",
            timestamp=first.timestamp + 1,
        )
        notes.save_board(board)

        char = create_test_character("Archivist", 3001)
        char.level = 45
        char.trust = 45

        output = process_command(char, "note catchup")
        assert output == "All mesages skipped."
        assert char.pcdata.last_notes[board.storage_key()] == second.timestamp

        follow_up = process_command(char, "note")
        assert "no new notes" in follow_up.lower()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_read_defaults_to_next_unread(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        board = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        first = board.post("Immortal", "Welcome", "Read the rules", timestamp=time.time())
        second = board.post(
            "Immortal",
            "Changes",
            "Policy update",
            timestamp=first.timestamp + 1,
        )
        notes.save_board(board)

        char = create_test_character("Reader", 3001)
        char.level = 50
        char.trust = 50

        output = process_command(char, "note")
        assert "Welcome" in output
        assert "Read the rules" in output
        assert char.pcdata.last_notes[board.storage_key()] == first.timestamp

        output = process_command(char, "note read")
        assert "Changes" in output
        assert "Policy update" in output
        assert char.pcdata.last_notes[board.storage_key()] == second.timestamp
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_read_advances_to_next_board_when_exhausted(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        general = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        general_note = general.post(
            "Immortal",
            "Welcome",
            "Read the rules",
            timestamp=time.time(),
        )
        ideas = notes.get_board(
            "Ideas",
            description="Suggestion board",
            read_level=0,
            write_level=0,
        )
        ideas_note = ideas.post(
            "Immortal",
            "Proposal",
            "Consider this",
            timestamp=general_note.timestamp + 1,
        )
        notes.save_board(general)
        notes.save_board(ideas)

        char = create_test_character("Seeker", 3001)
        char.level = 50
        char.trust = 50
        char.pcdata.last_notes[general.storage_key()] = general_note.timestamp

        message = process_command(char, "note")
        assert "No new notes" in message
        assert "Changed to next board, Ideas." in message
        assert char.pcdata.board_name == ideas.storage_key()

        follow_up = process_command(char, "note")
        assert "Proposal" in follow_up
        assert "Consider this" in follow_up
        assert char.pcdata.last_notes[ideas.storage_key()] == ideas_note.timestamp
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_board_change_blocked_during_note_draft(tmp_path):
    boards_dir = tmp_path / "boards"
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world("area/area.lst")
        character_registry.clear()
        general = notes.get_board(
            "General",
            description="General discussion",
            read_level=0,
            write_level=0,
        )
        ideas = notes.get_board(
            "Ideas",
            description="Suggestion board",
            read_level=0,
            write_level=0,
        )
        notes.save_board(general)
        notes.save_board(ideas)

        char = create_test_character("Scribe", 3001)
        char.level = 60
        char.trust = 60

        start = process_command(char, "note write")
        assert "general" in start.lower()

        blocked = process_command(char, "board ideas")
        assert blocked == "Please finish your interrupted note first."
        assert char.pcdata.board_name == general.storage_key()

        process_command(char, "note subject Plans")
        process_command(char, "note text Draft details")
        send_output = process_command(char, "note send")
        assert "posted" in send_output.lower()

        change_output = process_command(char, "board ideas")
        assert "ideas" in change_output.lower()
        assert char.pcdata.board_name == ideas.storage_key()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)
