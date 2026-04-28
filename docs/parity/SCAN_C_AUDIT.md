# `scan.c` Audit — ROM 2.4b6 → QuickMUD-Python Parity

**Status:** ✅ AUDITED — all 3 gaps closed (SCAN-001/002/003)
**Date:** 2026-04-28
**ROM C:** `src/scan.c` (141 lines, 3 functions)
**Python:** `mud/commands/inspection.py:do_scan` (lines 9-114)
**Priority:** P2 (gameplay-visible, but cosmetic in nature — broadcasts and headers)

## Phase 1 — Function Inventory

| ROM C function | ROM lines | Python equivalent | Status |
|----------------|-----------|-------------------|--------|
| `do_scan` | scan.c:48-104 | `mud/commands/inspection.py:9-114` (`do_scan`) | ⚠️ PARTIAL — broadcasts missing, headers diverge |
| `scan_list` | scan.c:106-123 | inlined as `list_room` helper inside `do_scan` (inspection.py:54-69) | ✅ AUDITED |
| `scan_char` | scan.c:125-141 | inlined inside `list_room` (inspection.py:64-68) | ✅ AUDITED |

## Phase 2 — Line-by-line Verification

### `do_scan` — no-arg branch (ROM scan.c:58-69)

ROM:
```c
if (arg1[0] == '\0') {
    act ("$n looks all around.", ch, NULL, NULL, TO_ROOM);
    send_to_char ("Looking around you see:\n\r", ch);
    scan_list (ch->in_room, ch, 0, -1);
    for (door = 0; door < 6; door++) {
        if ((pExit = ch->in_room->exit[door]) != NULL)
            scan_list (pExit->u1.to_room, ch, 1, door);
    }
    return;
}
```

Python (inspection.py:71-83):
- ✅ Header `"Looking around you see:"` matches.
- ✅ Iterates own room (depth 0) then 6 directions (depth 1) in N,E,S,W,U,D order.
- ❌ **No `act("$n looks all around.", ..., TO_ROOM)` broadcast.** Onlookers never see the scanner glance about. → **SCAN-001**.
- ⚠️ Adds `"No one is nearby."` fallback when nothing visible. ROM emits the header alone with no fallback. → **SCAN-003**.

### `do_scan` — directional branch (ROM scan.c:71-103)

ROM:
```c
act ("You peer intently $T.", ch, NULL, dir_name[door], TO_CHAR);
act ("$n peers intently $T.", ch, NULL, dir_name[door], TO_ROOM);
sprintf (buf, "Looking %s you see:\n\r", dir_name[door]);   /* <-- BUF NEVER SENT */
scan_room = ch->in_room;
for (depth = 1; depth < 4; depth++) { ... }
```

ROM C builds `buf` with the "Looking <dir> you see:" header but **never calls `send_to_char(buf, ch)`** — only the two `act()` calls produce visible TO_CHAR/TO_ROOM messages. (This is a long-standing ROM bug; we replicate it per parity rules.)

Python (inspection.py:104-114):
- ❌ **Missing `act("You peer intently $T.", TO_CHAR)`** — no "You peer intently north." line. → **SCAN-002**.
- ❌ **Missing `act("$n peers intently $T.", TO_ROOM)`** — no broadcast to room. → **SCAN-002**.
- ❌ **Emits `"Looking <dir> you see:"` header that ROM never sends.** → **SCAN-002** (same fix removes the spurious header and adds the act() pair).
- ⚠️ Adds `"Nothing of note."` fallback when nothing visible. ROM emits nothing in that case (only the two act() messages remain). → **SCAN-003**.

### `do_scan` — bad direction (ROM scan.c:83-87)

ROM: `send_to_char ("Which way do you want to scan?\n\r", ch);` ✅ matches Python.

### `scan_list` — visibility filter (ROM scan.c:106-123)

ROM:
```c
if (rch == ch) continue;
if (!IS_NPC (rch) && rch->invis_level > get_trust (ch)) continue;
if (can_see (ch, rch)) scan_char (rch, ch, depth, door);
```

Python (inspection.py:58-68): self-skip ✅; uses `can_see_character` ✅. The explicit `invis_level > get_trust` PC check is folded into `can_see_character` per existing handler audit; treated as ✅ AUDITED.

### `scan_char` — output formatting (ROM scan.c:125-141)

ROM emits `"<PERS>, <distance[depth] %% dir_name[door]>\n"`. For depth 0 the format string is `"right here."` with no `%s` — sprintf passes through unchanged.

Python (inspection.py:64-68): emits `"{who}, right here."` for depth 0 and `"{who}, {distance[depth] % dn}"` otherwise. ✅ Matches ROM format.

## Phase 3 — Gaps

| ID | Severity | ROM C ref | Python ref | Description | Status |
|----|----------|-----------|------------|-------------|--------|
| `SCAN-001` | IMPORTANT | `src/scan.c:60` | `mud/commands/inspection.py:74` | No-arg `do_scan` is missing the `act("$n looks all around.", TO_ROOM)` broadcast — onlookers never see the scan. | ✅ FIXED — `tests/integration/test_scan_broadcasts.py::test_scan_no_arg_broadcasts_looks_all_around` |
| `SCAN-002` | IMPORTANT | `src/scan.c:89-91` | `mud/commands/inspection.py:104-110` | Directional `do_scan` is missing both `act("You peer intently $T.", TO_CHAR)` and `act("$n peers intently $T.", TO_ROOM)`, and emits a spurious `"Looking <dir> you see:"` header that ROM builds but never sends. | ✅ FIXED — TO_CHAR returned to scanner, TO_ROOM via `broadcast_room`, header dropped. `tests/integration/test_scan_broadcasts.py::test_scan_directional_emits_peer_intently_pair` |
| `SCAN-003` | MINOR | `src/scan.c:48-104` | `mud/commands/inspection.py:84-86,116-118` | Python adds non-ROM fallback lines (`"No one is nearby."`, `"Nothing of note."`) when no visible characters are found; ROM emits nothing extra. | ✅ FIXED — both fallbacks removed. `tests/integration/test_scan_broadcasts.py::test_scan_empty_room_emits_no_fallback` |

No CRITICAL gaps. SCAN-001 and SCAN-002 are IMPORTANT (visible behavior — TO_ROOM and TO_CHAR messages diverge). SCAN-003 is MINOR cosmetic.

## Phase 4 — Closures

(Pending — to be filled in by `rom-gap-closer` per gap.)

## Phase 5 — Completion

✅ All three gaps closed on 2026-04-28:

- `SCAN-001` — TO_ROOM `"$n looks all around."` broadcast added (no-arg branch).
- `SCAN-002` — TO_CHAR/TO_ROOM `"You peer intently <dir>." / "$n peers intently <dir>."` act() pair added; spurious `"Looking <dir> you see:"` header removed (directional branch).
- `SCAN-003` — Non-ROM `"No one is nearby."` / `"Nothing of note."` fallback lines removed.

Coverage: `tests/integration/test_scan_broadcasts.py` (3 tests, all passing) plus the existing `tests/test_scan_parity.py` unit suite (13 tests, updated to ROM-faithful expectations).
