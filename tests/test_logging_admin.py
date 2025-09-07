from pathlib import Path

from mud.world import initialize_world, create_test_character
from mud.commands import process_command


def test_wiznet_toggle_is_logged(tmp_path, monkeypatch):
    # Direct logs to a temp directory
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    initialize_world('area/area.lst')
    admin = create_test_character('Admin', 3001)
    admin.is_admin = True

    out = process_command(admin, 'wiznet')
    assert 'Wiznet is now' in out

    log_path = Path('log') / 'admin.log'
    assert log_path.exists()
    text = log_path.read_text(encoding='utf-8')
    # Expect command name to appear in the log line
    assert '\twiznet\t' in text
    assert '\tAdmin\t' in text

