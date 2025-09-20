import time

import mud.notes as notes
from mud.commands.dispatcher import process_command
from mud.world import initialize_world, create_test_character
from mud.models.character import character_registry
from mud.models.board import BoardForceType
from mud import persistence


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
        notes.load_boards()
        initialize_world('area/area.lst')
        character_registry.clear()
        char = create_test_character('Author', 3001)
        char.level = 5
        output = process_command(char, 'note post Hello|This is a test')
        assert 'posted' in output.lower()
        list_output = process_command(char, 'note list')
        assert 'hello' in list_output.lower()
        assert char.pcdata is not None
        assert char.pcdata.last_notes.get('general', 0) > 0
        notes.board_registry.clear()
        notes.load_boards()
        list_output2 = process_command(char, 'note list')
        assert 'hello' in list_output2.lower()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_board_switching_and_unread_counts(tmp_path):
    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world('area/area.lst')
        character_registry.clear()
        general = notes.get_board(
            'General',
            description='General discussion',
            read_level=0,
            write_level=0,
        )
        ideas = notes.get_board(
            'Ideas',
            description='Suggestions',
            read_level=0,
            write_level=0,
        )
        personal = notes.get_board(
            'Personal',
            description='Personal messages',
            read_level=60,
            write_level=60,
        )
        general.post('Immortal', 'Welcome', 'Read the rules')
        notes.save_board(general)

        char = create_test_character('Reader', 3001)
        char.level = 10
        board_output = process_command(char, 'board')
        assert 'general' in board_output.lower()
        assert '[  1]' in board_output
        assert '[  0]' in board_output
        change_output = process_command(char, 'board 2')
        assert 'ideas' in change_output.lower()
        assert char.pcdata.board_name == ideas.storage_key()
        deny_output = process_command(char, 'board personal')
        assert deny_output == 'No such board.'
        assert char.pcdata.board_name == ideas.storage_key()
        char.trust = 60
        allow_output = process_command(char, 'board personal')
        assert 'personal' in allow_output.lower()
        assert char.pcdata.board_name == personal.storage_key()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_board_switching_persists_last_note(tmp_path):
    boards_dir = tmp_path / 'boards'
    players_dir = tmp_path / 'players'
    orig_board_dir = _setup_boards(boards_dir)
    orig_players = persistence.PLAYERS_DIR
    persistence.PLAYERS_DIR = players_dir
    try:
        initialize_world('area/area.lst')
        character_registry.clear()
        general = notes.get_board(
            'General',
            description='General discussion',
            read_level=0,
            write_level=0,
        )
        ideas = notes.get_board(
            'Ideas',
            description='Suggestions',
            read_level=0,
            write_level=0,
        )
        char = create_test_character('Archivist', 3001)
        char.level = 50
        char.trust = 50

        post_output = process_command(char, 'note post Hello|First note')
        assert 'posted' in post_output.lower()
        switch_output = process_command(char, 'board ideas')
        assert 'ideas' in switch_output.lower()
        assert char.pcdata.board_name == ideas.storage_key()

        persistence.save_character(char)

        general.post('Immortal', 'Update', 'New policies', timestamp=time.time() + 1)
        notes.save_board(general)
        notes.save_board(ideas)

        notes.board_registry.clear()
        notes.load_boards()
        character_registry.clear()

        loaded = persistence.load_character('Archivist')
        assert loaded is not None
        assert loaded.pcdata.board_name == ideas.storage_key()
        board_listing = process_command(loaded, 'board')
        assert 'ideas' in board_listing.lower()
        assert '[  1]' in board_listing
    finally:
        character_registry.clear()
        _teardown_boards(orig_board_dir)
        persistence.PLAYERS_DIR = orig_players


def test_board_listing_retains_current_board_without_access(tmp_path):
    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world('area/area.lst')
        character_registry.clear()
        general = notes.get_board(
            'General',
            description='General discussion',
            read_level=0,
            write_level=0,
        )
        personal = notes.get_board(
            'Personal',
            description='Personal messages',
            read_level=60,
            write_level=60,
        )
        notes.save_board(general)
        notes.save_board(personal)

        char = create_test_character('Scout', 3001)
        char.level = 30
        char.trust = 30
        char.pcdata.board_name = personal.storage_key()

        output = process_command(char, 'board')
        assert 'personal' in output.lower()
        assert 'cannot read or write' in output.lower()
        assert char.pcdata.board_name == personal.storage_key()
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_board_listing_falls_back_to_default_when_missing(tmp_path):
    orig_dir = _setup_boards(tmp_path)
    try:
        initialize_world('area/area.lst')
        character_registry.clear()
        general = notes.get_board(
            'General',
            description='General discussion',
            read_level=0,
            write_level=0,
        )
        notes.save_board(general)

        char = create_test_character('Traveler', 3001)
        char.level = 10
        char.pcdata.board_name = 'ghost'

        output = process_command(char, 'board')
        assert 'general' in output.lower()
        assert char.pcdata.board_name == general.storage_key()
        assert notes.find_board('ghost') is None
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_write_pipeline_enforces_defaults(tmp_path):
    boards_dir = tmp_path / 'boards'
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world('area/area.lst')
        character_registry.clear()
        board = notes.get_board(
            'Immortal',
            description='Immortal discussions',
            read_level=0,
            write_level=0,
            default_recipients='imm',
            force_type=BoardForceType.INCLUDE,
        )
        notes.save_board(board)

        char = create_test_character('Scribe', 3001)
        char.level = 60
        char.trust = 60

        process_command(char, 'board immortal')

        start_output = process_command(char, 'note write')
        assert 'immortal' in start_output.lower()
        assert 'must include imm' in start_output.lower()

        set_to = process_command(char, 'note to mortal')
        assert 'mortal imm' in char.pcdata.in_progress.to.lower()
        assert 'mortal imm' in set_to.lower()

        subject_output = process_command(char, 'note subject Policy Update')
        assert 'policy update' in subject_output.lower()

        text_output = process_command(char, 'note text Follow the law.')
        assert 'updated' in text_output.lower()

        send_output = process_command(char, 'note send')
        assert 'posted' in send_output.lower()
        assert board.notes[-1].to.lower() == 'mortal imm'
        assert char.pcdata.in_progress is None
        assert char.pcdata.last_notes[board.storage_key()] == board.notes[-1].timestamp
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)


def test_note_remove_and_catchup(tmp_path):
    boards_dir = tmp_path / 'boards'
    orig_dir = _setup_boards(boards_dir)
    try:
        initialize_world('area/area.lst')
        character_registry.clear()
        board = notes.get_board(
            'General',
            description='General discussion',
            read_level=0,
            write_level=0,
        )
        board.post('Scribe', 'Hello', 'Testing removal', timestamp=time.time())
        second = board.post('Immortal', 'Rules', 'Read carefully', timestamp=time.time() + 1)
        notes.save_board(board)

        char = create_test_character('Scribe', 3001)
        char.level = 50
        char.trust = 50

        remove_output = process_command(char, 'note remove 1')
        assert 'removed' in remove_output.lower()
        assert len(board.notes) == 1
        assert board.notes[0] == second

        catchup_output = process_command(char, 'note catchup')
        assert 'skipped' in catchup_output.lower()
        assert char.pcdata.last_notes[board.storage_key()] == second.timestamp
    finally:
        character_registry.clear()
        _teardown_boards(orig_dir)
