"""DUPL-001a regression: immortal-command stubs must not write to the
``output_buffer`` black hole.

Before this fix, 9 imm_*/admin/remaining_rom modules carried identical
``_send_to_char`` stubs that appended to ``char.output_buffer`` — an
attribute the production connection read loop never drains.  Every
message routed through those stubs vanished.

After consolidation onto ``mud/utils/messaging.py:send_to_char_buffered``,
messages reach the canonical channels: ``asyncio.create_task(send_to_char)``
for connected PCs, ``char.messages`` mailbox for disconnected/tests.

This test pins the contract at one representative site (`do_protect` in
``mud/commands/imm_punish.py``) — exhaustive imm-command coverage lives
in the per-command audit suites.

See ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-001a).
"""

from __future__ import annotations

from mud.commands.imm_punish import _send_to_char
from mud.models.character import Character


def test_send_to_char_does_not_use_output_buffer_attribute() -> None:
    """After DUPL-001a, no imm_* command writes to ``char.output_buffer``."""

    pc = Character(name="ghost", is_npc=False)
    assert getattr(pc, "connection", None) is None

    _send_to_char(pc, "Test message.")

    # Canonical mailbox fallback delivered the message.
    assert "Test message." in pc.messages
    # The legacy black-hole attribute must NOT be created.
    assert not hasattr(pc, "output_buffer"), (
        "imm_* _send_to_char still creating char.output_buffer — "
        "DUPL-001a regression. The production read loop never drains "
        "this attribute, so messages would vanish."
    )
