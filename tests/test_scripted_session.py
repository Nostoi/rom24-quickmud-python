"""Integration test that exercises a short scripted command sequence."""

from mud.commands import run_test_session


def test_scripted_session_transcript():
    """Run the canned test session and verify key command responses."""
    outputs = run_test_session()
    assert "Temple" in outputs[0]
    # ROM act_move.c:204 — moving north shows the destination room (do_look "auto"),
    # not a "You walk north" line. The scripted walk lands in the Temple of Mota.
    assert "Temple Of Mota" in outputs[1]
    assert "sword" in outputs[2].lower()
    assert "hello" in outputs[3].lower()
