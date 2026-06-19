# Session Summary — 2026-06-19 — DELETE-002 (do_delete staff wiznet broadcasts)

## Scope

Picked up from the completed STEAL-015 close (prior session, v2.14.129). Per-file
audit tracker is exhausted; cross-file / divergence-class sweep is the active
mode. From the open follow-ups in `SESSION_STATUS.md`, closed the highest-yield
concrete documented gap: **DELETE-002** — `do_delete` emitted neither of ROM's
two staff `wiznet` lines, so immortals got no notice when a character armed or
completed self-deletion.

## Outcomes

### `DELETE-002` — ✅ FIXED (genuine parity gap)

- **Python**: `mud/commands/player_config.py:do_delete`
- **ROM C**: `src/act_comm.c:92` (request pass) + `:62` (confirm pass)
- **Gap**: DELETE-002 — ROM `do_delete` broadcasts two `wiznet` lines staff see:
  `"$N is contemplating deletion."` on the first/request pass (`:92`,
  `min_level = get_trust(ch)`) and `"$N turns $Mself into line noise."` on the
  confirm/delete pass (`:62`, `min_level = 0`). The Python port emitted neither.
  Surfaced 2026-06-14 while closing DELETE-001 (an old audit note had wrongly
  dismissed it as an "acceptable difference").
- **Fix**: added both `wiznet(...)` calls to `do_delete`, mirroring the ROM
  ordering — the confirm-pass broadcast fires **before** the `do_quit` +
  `delete_character` tail (while `char` is still valid, exactly as ROM fires it
  before `do_quit`/`unlink`). Both calls route through the existing
  `mud.wiznet.wiznet` chokepoint, which already does act-format (`$N`/`$M`) and
  single-delivery via `push_message` — no new delivery path, INV-001-clean.
- **Tests**: `tests/test_wiznet.py` — 2 new, both fail-firsted (watcher received
  nothing before the fix):
  - `test_do_delete_request_broadcasts_contemplating_deletion_wiznet`
  - `test_do_delete_confirm_broadcasts_line_noise_wiznet` (stubs the heavy
    quit/delete tail via monkeypatch; asserts `$Mself` → "himself" from the
    deleter's sex).
- **Commit**: `d6fc8c53`, v2.14.130

## Files Modified

- `mud/commands/player_config.py` — `do_delete`: added the two `wiznet` calls
  (request pass at `get_trust(ch)`, confirm pass at `min_level=0` before the
  quit/unlink tail), each with a DELETE-002 why-comment citing ROM C.
- `tests/test_wiznet.py` — `_deleter_character` helper + 2 new tests; imported
  `PCData`.
- `docs/parity/ACT_COMM_C_AUDIT.md` — DELETE-002 row 🔄 OPEN → ✅ FIXED.
- `CHANGELOG.md` — Fixed entry (DELETE-002).
- `pyproject.toml` — 2.14.129 → 2.14.130.

## Test Status

- `pytest -n0 tests/test_wiznet.py tests/test_account_auth.py` — **92 passing**.
- `ruff check mud/commands/player_config.py tests/test_wiznet.py` — clean.
- `gitnexus_detect_changes` — low risk; scope = `do_delete` (+ `do_delet`
  line-shift neighbor) + the audit doc only. 0 affected processes.
- Full suite not re-run this session (change is localized to one command +
  its dedicated test file; area suites green).

## Next Steps

Remaining open follow-ups (from prior handoff, minus DELETE-002):
- **INV-050 bool-retirement** — still GATED on the `is_safe_spell`-vs-ROM
  standalone audit (`src/fight.c:1126-1218`).
- `mud/entrypoint.py` dead code; the `do_yell` hand-rolled-XOR tidy-up.
- Higher-yield enumeration-independent lever per
  `docs/parity/DIVERGENCE_CLASS_ROSTER.md`: Hypothesis state-machine →
  diff_harness widening (Class 11 / Phase C).
