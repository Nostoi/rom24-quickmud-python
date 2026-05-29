# Session Summary — 2026-05-29 — FIGHT-029 (do_rescue SINGLE-DELIVERY)

## Scope

Continued from the MAGIC-003 handoff. `SESSION_STATUS.md` named **FIGHT-029**
(the `do_rescue` SINGLE-DELIVERY violation surfaced by the advisor while closing
MAGIC-003) as the single next task. Closed via the standard gap-closer TDD flow
(failing test → fix → tracker/changelog/version → single commit). The advisor
pass after the fix surfaced a second, distinct `do_rescue` divergence — the
missing `check_killer` PK flag — filed durably as **FIGHT-030** (not folded into
the FIGHT-029 commit). Stays in the INV-001 SINGLE-DELIVERY family.

## Outcomes

### `FIGHT-029` — ✅ FIXED (2.11.25, `da73d821`)

- **Python**: `mud/skills/handlers.py:rescue` + `mud/commands/combat.py:do_rescue`
- **ROM C**: `src/fight.c:3089-3091` (the three `act()` success legs:
  TO_CHAR / TO_VICT / TO_NOTVICT), `:3084` (fail line) — `do_rescue` is **void**;
  all output writes straight to the descriptor, no return-value channel.
- **Gap**: two distinct bugs in one flow. **(1) Rescuer double-delivery** (the
  `do_kill`/FIGHT-020 + `do_surrender` shape): `rescue()` did
  `caster.messages.append(char_msg)` **and** `do_rescue` returned the same line;
  the connection loop sends a command's return value AND drains `char.messages`,
  so a connected PC rescuer got `"You rescue X!"` twice. **(2) Victim/room
  wrong-channel** (the MAGIC-003 shape): the TO_VICT / TO_NOTVICT legs were
  appended to `target.messages` / `occupant.messages` only, so a connected
  victim/bystander saw them late on their next command drain rather than
  immediately via the async push.
- **Fix**: `rescue()` now delivers all three legs via `_send_to_char` (canonical
  single-delivery channel; mailbox fallback preserved for disconnected
  chars/tests, ROM's TO_NOTVICT caster+target exclusion preserved so the
  opponent still sees the room line). `do_rescue` returns `""` on success; the
  fail-path `"You fail the rescue."` `char.messages.append` was likewise dropped
  (return-channel only, matching the `do_kill` guard convention).
- **Tests**: `tests/integration/test_rescue_single_delivery.py` —
  **split-shape** (advisor catch): the rescuer success line asserts
  **count-once** (the kill/surrender double), while victim + bystander assert
  **push-present & mailbox-empty** (the MAGIC-003 wrong-channel — a pure
  double-delivery count test *false-greens* on the vict/room legs, which are
  delayed-in-mailbox not duplicated). Fail-first verified all three failure
  modes via inline repro (vict/room `conn.sent == []`, lines stranded in
  mailbox; rescuer line 2×). Existing rescue tests realigned to the void
  contract: `test_skills.py` (`out == ""`), `test_skill_combat_rom_parity.py`
  (2 success tests → assert `char.messages` mailbox), `test_skills_integration.py`
  (robust to result-or-mailbox).

### `FIGHT-030` — filed (🔄 OPEN) — `do_rescue` omits `check_killer` PK flagging

- **Python**: `mud/skills/handlers.py:rescue` (the `stop_fighting`/`set_fighting`
  block) — no `check_killer(caster, foe)` call.
- **ROM C**: `src/fight.c:3097` — `check_killer(ch, fch)` between the two
  `stop_fighting` and the two `set_fighting` calls.
- **Gap**: ROM flags the rescuer as a killer when it joins combat against `fch`.
  The kill-stealing guard only blocks when `fch` is an NPC, so a PC *may* rescue
  an ally fighting **another PC** — the exact PvP case ROM flags (`PLR_KILLER` +
  killer timer). `check_killer` is a real wired function
  (`mud/combat/engine.py:1251`; used by `do_kill`/`do_murder`), not a stub, so
  the Python rescuer escapes PK consequences. Filed in `FIGHT_C_AUDIT.md`
  (FIGHT-030). Fix: add `check_killer(caster, foe)` between the `stop_fighting`
  and `set_fighting` pairs; test asserts `PlayerFlag.KILLER` on the rescuer when
  rescuing an ally fighting another non-clan/non-killer PC.

## Files Modified

- `mud/skills/handlers.py` — `rescue` three legs onto `_send_to_char` (FIGHT-029)
- `mud/commands/combat.py` — `do_rescue` returns `""`; fail-path append dropped (FIGHT-029)
- `tests/integration/test_rescue_single_delivery.py` — new (1 split-shape test)
- `tests/test_skills.py`, `tests/test_skill_combat_rom_parity.py`,
  `tests/integration/test_skills_integration.py` — realigned to the void contract
- `docs/parity/FIGHT_C_AUDIT.md` — FIGHT-029 → ✅ FIXED; FIGHT-030 row added (🔄 OPEN)
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-001 (c) → FIXED; (d)
  "still recovering" sweep added (OPEN); "Touched by" trail + status note
- `CHANGELOG.md` — `[2.11.25]` Fixed entry
- `pyproject.toml` — 2.11.24 → 2.11.25

Commit: `da73d821` (FIGHT-029). FIGHT-030 row + this handoff are a docs-only follow-up.

## Test Status

- `tests/integration/test_rescue_single_delivery.py` — 1/1 (FIGHT-029).
- All rescue-related tests (17 across 7 files) — green.
- 10-file combat/skills/single-delivery surface, serial (`-n0`) — 215 passed, 2 skipped.
- **Full suite**: **4974 passed, 4 skipped** (+1 vs prior 4973 from the new
  rescue test).
- `ruff check` on touched files: the 7 errors (handlers.py 672/1783/3518/3665/6298,
  combat.py 727, test_skills.py:1 import sort) are all **pre-existing** —
  verified identical on `HEAD` before the commit; none in edited regions.
- `gitnexus_detect_changes`: LOW risk, 0 affected processes (`_find_room_target`
  + `TestBerserkRomParity` flagged are diff-boundary adjacency artifacts —
  verified untouched). Reindexed after the commit (exit 0).

## Outstanding

- **`FIGHT-030` (OPEN)** — `do_rescue` missing `check_killer(caster, foe)` PK
  flagging (above). Local single-function divergence; `rom-gap-closer FIGHT-030`.
- **INV-001 (d) — `"You are still recovering."` cross-command sweep (OPEN)** —
  the wait-state guard does `char.messages.append(...)` AND returns/queues the
  same string in 7 `mud/commands/combat.py` commands (`do_kick`, `do_rescue`,
  + 5 others) and `mud/skills/registry.py:163` → double-delivery to a connected
  PC (the FIGHT-029 fail-path shape). Not a ROM line (ROM enforces wait at the
  interpreter, no message). Fix in one sweep: drop the append, keep the return.
  Durable locators: command names + `grep "still recovering" mud/` (exact line
  numbers in the tracker shifted after this session's comment edits — don't trust
  them).
- **`test_backstab_uses_position_and_weapon` parallel flake** (observed this
  session, pre-existing) — failed once under the default parallel run when the
  4 single-delivery test files were added to the batch (different xdist worker
  grouping). Passes serial (`-n0`), passes on the clean tree, and passed in the
  full parallel suite this session. The backstab test fully monkeypatches
  `number_percent`/`dice`, so it is a cross-file *state* leak (a sibling on the
  same worker), not an RNG-seed issue — the AGENTS.md "Parallel test execution &
  isolation" hazard class. Root-cause the leaking sibling if it recurs; do not
  just re-run.
- **Converter hardening** — `convert_skills_to_json.py` is lossy (drops
  hand-added `cancellation`/`harm`); make it merge-not-replace. Interim guard in
  the script docstring (`86eee6ef`).
- **Object targeting in `do_cast`** — `TAR_OBJ_CHAR_*` object-target legs
  (`src/magic.c:502-506`, `:525-529`) and `TAR_OBJ_INV` fall back to the caster;
  named-not-found returns `"They aren't here."` not ROM's
  `"You don't see that here."` (deferred, MAGIC_C_AUDIT Scope Notes).
- **`SHOP-PET-002`** (open, `FIGHT_C_AUDIT.md`) — pet purchase should
  `create_mobile(pIndexData)` (fresh re-roll), not clone the template.
- **`test_combat_death.py` xdist flake** (carried) — seed RNG in the unit death tests.
- Stray uncommitted 1-line doc tweak to
  `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (present across sessions;
  unrelated to parity — left uncommitted).

## Next Steps

The cleanest next gap is **FIGHT-030** (`do_rescue` `check_killer` —
`rom-gap-closer FIGHT-030`), which stays in the `do_rescue` context already
loaded. After that, the **INV-001 (d) "still recovering" sweep** is a small,
well-scoped cross-command cleanup (one commit, drop-the-append in ~8 sites).
Beyond those, the per-file audit tracker is exhausted; cross-file invariants
(`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md`) remains the standing pass —
the return-value-plus-mailbox (`do_rescue`/`do_surrender`/`do_kill`) shape keeps
surfacing INV-001 siblings, so a targeted sweep for that pattern is high-yield.
