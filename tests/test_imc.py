import os

from mud.imc import imc_enabled, maybe_open_socket
from mud.imc.protocol import parse_frame, serialize_frame, Frame


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

