from pathlib import Path

from mud.world import initialize_world, create_test_character
from mud.commands import process_command


def test_wiznet_toggle_is_logged():
    # Ensure clean log file
    log_path = Path('log') / 'admin.log'
    if log_path.exists():
        log_path.unlink()

    initialize_world('area/area.lst')
    admin = create_test_character('Admin', 3001)
    admin.is_admin = True

    out = process_command(admin, 'wiznet')
    assert 'Wiznet is now' in out

    assert log_path.exists()
    text = log_path.read_text(encoding='utf-8')
    # Expect command name to appear in the log line
    assert '\twiznet\t' in text
    assert '\tAdmin\t' in text
