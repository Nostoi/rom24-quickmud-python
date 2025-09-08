from mud.imc import imc_enabled, maybe_open_socket
from mud.imc.protocol import parse_frame, serialize_frame, Frame
from mud.world import initialize_world, create_test_character
from mud.commands import process_command


def test_imc_disabled_by_default(monkeypatch):
    monkeypatch.delenv('IMC_ENABLED', raising=False)
    assert imc_enabled() is False
    # Must not open sockets when disabled
    assert maybe_open_socket() is None


def test_parse_serialize_roundtrip():
    sample = "chat alice@quickmud * :Hello world"
    frame = parse_frame(sample)
    assert frame == Frame(type='chat', source='alice@quickmud', target='*', message='Hello world')
    assert serialize_frame(frame) == sample


def test_parse_invalid_raises():
    for s in ["", "badframe", "chat onlytwo", "chat a b c"]:
        try:
            parse_frame(s)
            assert False
        except ValueError:
            pass


def test_imc_command_gated(monkeypatch):
    monkeypatch.delenv('IMC_ENABLED', raising=False)
    initialize_world('area/area.lst')
    ch = create_test_character('IMCUser', 3001)
    out = process_command(ch, 'imc')
    assert 'disabled' in out.lower()


def test_imc_command_enabled_help(monkeypatch):
    monkeypatch.setenv('IMC_ENABLED', 'true')
    initialize_world('area/area.lst')
    ch = create_test_character('IMCUser', 3001)
    out = process_command(ch, 'imc help')
    assert 'enabled' in out.lower()
    # Ensure gate causes networking to raise if attempted
    try:
        maybe_open_socket()
        assert False
    except NotImplementedError:
        pass
