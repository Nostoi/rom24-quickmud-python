"""Guard: production code must not deliver to a character's ``messages`` mailbox
directly — connected PCs must receive output through the single-delivery
chokepoint, never the mailbox alone.

ROM C ``src/comm.c:write_to_buffer`` writes one message to a player's descriptor:
a single delivery channel.  Python cannot do synchronous socket writes inside the
synchronous game tick, so connected characters receive messages via
``asyncio.create_task(send_to_char(...))`` and the ``char.messages`` list is a
**test / disconnected-character fallback only** (see AGENTS.md "Message Delivery
(Architectural Divergence)" and ``docs/divergences/MESSAGE_DELIVERY.md``).

Two failure modes this scanner exists to catch — both INV-001 SINGLE-DELIVERY
violations (``docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md``):

1. **Mailbox-only for a connected PC.** The connection read loop drains
   ``char.messages`` only after the player's *next* command, so a message
   appended to the mailbox during a tick is invisible until the player types
   something.  This was SPEC-017 (spec-fun room flavor) and the tick-aggression
   class of v2.14.115.
2. **Dual delivery.** Appending to *both* the async send and the mailbox replays
   the line on the next prompt for connected PCs.

The canonical chokepoint is ``mud.utils.messaging.push_message`` (and
``send_to_char_buffered``), which routes a connected PC to the async socket
*xor* the mailbox.  Use it instead of touching ``<entity>.messages`` directly.

This is the same static-guard pattern as ``test_rng_determinism.py`` and
``test_equipment_key_convention.py`` (Layer-A in
``docs/parity/DIVERGENCE_CLASS_ROSTER.md``).

Allowlist policy
----------------
``_LEGITIMATE`` holds the genuine single-delivery chokepoints, the mailbox
accessor, and the read-only mailbox inspectors — these are correct by design.

``_INV001_DEBT`` holds known mailbox bypasses not yet migrated to the chokepoint,
frozen here so the guard ships green while preventing *new* bypasses.  Each is an
INV-001 "Touched by" site in the cross-file tracker; fixing one means routing it
through ``push_message`` and deleting its line below.  The orphan check keeps the
allowlist honest: an entry that no longer matches any line fails the test, so a
closed debt entry cannot rot.

NOTE: ``skill.messages`` is a dict of ROM message templates, NOT a character
mailbox — the ``getattr(skill, ...)`` form is excluded by the pattern below.
"""

from __future__ import annotations

import re
from pathlib import Path

# (A) Direct mailbox write: `<entity>.messages.append(...)`.
_APPEND_PATTERN = re.compile(r"\.messages\.append\s*\(")

# (B) Foreign-mailbox handle acquisition: `getattr(<id>, "messages")` — the first
# half of the two-step `m = getattr(x, "messages"); m.append(...)` bypass idiom
# that pattern (A) cannot see.  `skill` is excluded: `skill.messages` is a
# message-template dict, not a character mailbox.
_GETATTR_PATTERN = re.compile(r"""getattr\(\s*([A-Za-z_]\w*)\s*,\s*["']messages["']""")

_SCAN_DIR = "mud"

# Genuine single-delivery chokepoints / accessors / read-only inspectors.
_LEGITIMATE: set[tuple[str, str]] = {
    # push_message — the canonical chokepoint; mailbox is the disconnected/test fallback.
    ("mud/utils/messaging.py", 'mailbox = getattr(character, "messages", None)'),
    # broadcast_room / broadcast_global — async-xor-mailbox (mailbox in the elif).
    ("mud/net/protocol.py", "char.messages.append(message)"),
    ("mud/net/protocol.py", "char.messages.append(per_message)"),
    # Character.send_to_char — the mailbox accessor itself.
    ("mud/models/character.py", "self.messages.append(message)"),
    # _push_music_message — async-xor-mailbox (mailbox in the elif).
    ("mud/music/__init__.py", "recipient.messages.append(message)"),
    # healer "before/after" diff — READS the mailbox, never writes.
    ("mud/commands/healer.py", 'messages = getattr(char, "messages", None)'),
    ("mud/commands/healer.py", 'start_index = len(getattr(char, "messages", []) or [])'),
}

# Known INV-001 mailbox bypasses awaiting migration to push_message.
# Each is an INV-001 "Touched by" site in CROSS_FILE_INVARIANTS_TRACKER.md.
# Fix = route through push_message + delete its line here.
_INV001_DEBT: set[tuple[str, str]] = {
    ("mud/commands/communication.py", "target.messages.append(message)"),
}

_ALLOWED = _LEGITIMATE | _INV001_DEBT


def _scan() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in sorted(Path(_SCAN_DIR).rglob("*.py")):
        rel = path.as_posix()
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            code = line.split("#", 1)[0]  # ignore comments citing the anti-pattern
            if _APPEND_PATTERN.search(code):
                hits.append((rel, lineno, line.strip()))
                continue
            m = _GETATTR_PATTERN.search(code)
            if m and m.group(1) != "skill":
                hits.append((rel, lineno, line.strip()))
    return hits


def test_no_unsanctioned_mailbox_delivery_in_production() -> None:
    offenders = [f"{rel}:{n}: {text}" for rel, n, text in _scan() if (rel, text) not in _ALLOWED]
    assert not offenders, (
        "Direct char.messages mailbox delivery found outside the single-delivery "
        "chokepoint. Connected PCs must receive via mud.utils.messaging.push_message "
        "(async socket xor mailbox), never the mailbox alone (INV-001 SINGLE-DELIVERY; "
        "see AGENTS.md 'Message Delivery'). If this is a genuine chokepoint add it to "
        "_LEGITIMATE; if it is a known bypass add it to _INV001_DEBT with a tracker row:\n" + "\n".join(offenders)
    )


def test_allowlist_has_no_orphan_entries() -> None:
    """Self-cleaning: an allowlist entry that no longer matches any line is stale
    (the site was fixed or moved) and must be removed, keeping the ratchet honest."""
    live = {(rel, text) for rel, _, text in _scan()}
    orphans = sorted(_ALLOWED - live)
    assert not orphans, (
        "Stale message-delivery allowlist entries (no matching line — fixed or moved). "
        "Remove them from _LEGITIMATE / _INV001_DEBT:\n" + "\n".join(f"{r}: {t}" for r, t in orphans)
    )
