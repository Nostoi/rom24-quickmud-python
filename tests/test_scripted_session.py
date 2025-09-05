"""Integration test that exercises a short scripted command sequence."""

from mud.commands import run_test_session


def test_scripted_session_transcript():
    """Run the canned test session and verify key command responses."""
    outputs = run_test_session()
    assert "Temple" in outputs[0]
    assert "long sword" in outputs[1]
    assert "north" in outputs[2]
    assert "hello" in outputs[3].lower()
