# Session Summary — 2026-05-30 — INV-029 ACT-FIRST-LETTER-CAP (ENFORCED)

## Scope

Continuation picking up **Next Task #1** from `SESSION_STATUS.md`: close the
cross-cutting **ACT-FIRST-LETTER-CAP** divergence and promote it to a stable
cross-file invariant (**INV-029**). ROM `act_new` upper-cases the first visible
letter of *every* rendered `act()` line; the Python act-family did not. The
handoff flagged this as wide blast radius ("Do NOT land blind — needs a reliable
channel to run the full suite"). This session confirmed the test channel works,
re-scoped per the advisor (the grep'd "61 files" was an overcount), enforced at
the two real render boundaries, and ran the full-suite assertion sweep.

One code commit landed: `7e9c488c` (`fix(parity)`, 2.11.38). The handoff commit
(this summary + `SESSION_STATUS.md` + the tracker status-cell honesty fix +
README badge/metric refresh) is separate.

## Outcomes

### `INV-029` — ACT-FIRST-LETTER-CAP — ✅ ENFORCED (2.11.38, `7e9c488c`)

- **ROM C**: `src/comm.c:2376-2379` (`act_new`) — after the per-recipient buffer
  is formatted, ROM caps `buf[0]` with a colour-code kludge: `if (buf[0]=='{')`
  cap `buf[2]` (the char after the 2-char `{X` code), else `buf[0]`. `UPPER`
  (`src/merc.h`) flips ASCII `a`–`z` only.
- **Gap**: a masked `$n`/`$N` rendering `"someone"` at sentence start showed
  `"someone …"` instead of ROM's `"Someone …"`, and any lowercase-led act line
  (object/mob short_descrs, jukebox lines) was never capitalized. Natural
  completion of INV-027 (ACT-PERS-NAME-MASKING).
- **Fix**: new shared helper `mud/utils/act.py:capitalize_act_line` (replicates
  the `{`-kludge + ASCII-only UPPER, guards empty / `<3`-char) applied at the
  two render boundaries the port uses:
  - **(a)** `mud/utils/act.py:act_format`'s return — the ~113-call-site `act_new`
    equivalent. **Gating check** (advisor-required): the only `act_format`
    result interpolated into a larger string (music `f"{prefix} {suffix}"`,
    `mud/music/__init__.py:207`) is sentence-start, so capping there is correct;
    no mid-sentence concatenation exists.
  - **(b)** the `mud/commands/imm_commands.py` `pers()`-built f-strings that
    bypass `act_format`: `do_force` ×4 (`:339,354,369,399`), `do_transfer`
    (`:290`), `_act_room`, `_act_room_invis_gated`.
- **Safety**: `gitnexus_impact(act_format)` = **CRITICAL** (43 direct callers,
  83 impacted) — expected and reported, since this deliberately changes the
  first letter of every act line; the "blast radius" is a test-assertion sweep,
  not logic breakage. `gitnexus_detect_changes` = **low**, 0 affected processes,
  scope = the act-render functions + swept tests + docs.
- **Tests**: `tests/integration/test_inv029_act_first_letter_cap.py` (7) —
  helper `{`-kludge / ASCII-only / empty-short edge cases + `act_format`
  plain-line + `act_format` masked-name-at-start + `do_force` masked-name.
  Failing-first confirmed in stages: ImportError red → path (a) green / path (b)
  still red (proving the second render path is genuinely separate) → both green.

### Full-suite assertion sweep (15 assertions, all ROM-faithful sentence-start caps)

Each was verified as a sentence-start cap (ROM-correct → update assertion), not
a logic regression:

- `tests/test_spec_funs.py` (5): adept/nasty/troll/ogre mob short_descr lines
  `"a …"` → `"A …"`.
- `tests/test_wiznet.py` (4): `_wiznet_payload` exact-matches — capitalized the
  expected text (payload `"{Z"` prefix → ROM caps `buf[2]`, the first char of
  the message). Confirmed the cap lands on the inner message before the `{Z`
  prefix is prepended in `_wiznet_deliver`.
- `tests/integration/test_music_play.py` (4 across 2 asserts pairs): jukebox
  `"the jukebox/something starts playing…"` + `"…bops:…"` → capitalized
  (the `$p` prefix leads the line).
- `tests/test_networking_telnet.py` (1): `"the wraith has returned…"` → `"The …"`.
- `tests/integration/test_inv027_act_pers_name_masking.py` (1): masked
  `"someone grins slyly."` → `"Someone …"`.
- **WIZ-047/048/049 lockstep** (3): `test_wiz047_…::test_act_room_masks…`,
  `test_act_wiz_command_parity.py::test_transfer_masks…` + `::test_force_masks…`
  — `"someone"` → `"Someone"` (these asserted lowercase deliberately and were
  documented to move in lockstep when ACT-FIRST-LETTER-CAP closed).

## Files Modified

Code commit `7e9c488c` (14 files):

- `mud/utils/act.py` — new `capitalize_act_line` helper; `act_format` caps its return.
- `mud/commands/imm_commands.py` — cap applied at `do_force` ×4 / `do_transfer` / `_act_room` / `_act_room_invis_gated`; top-level `capitalize_act_line` import.
- `tests/integration/test_inv029_act_first_letter_cap.py` — NEW, 7 tests.
- `tests/test_spec_funs.py`, `tests/test_wiznet.py`, `tests/integration/test_music_play.py`, `tests/test_networking_telnet.py`, `tests/integration/test_inv027_act_pers_name_masking.py`, `tests/integration/test_act_wiz_command_parity.py`, `tests/integration/test_wiz047_transfer_pers_name_masking.py` — assertion sweep (15 flips + comments).
- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-029 table row + INV-027 entry updated (ACT-FIRST-LETTER-CAP closed).
- `docs/parity/ACT_WIZ_C_AUDIT.md` — ACT-FIRST-LETTER-CAP note → CLOSED/INV-029.
- `CHANGELOG.md` — 2.11.38 section.
- `pyproject.toml` — 2.11.37 → 2.11.38.

Handoff commit (separate): this summary, `SESSION_STATUS.md`, the
`CROSS_FILE_INVARIANTS_TRACKER.md` INV-029 **status-cell honesty fix** (combat
damage messages surfaced as a prominent OPEN cousin, INV-001 idiom), and
`README.md` badge/metric refresh (version 2.11.38, tests 5002).

## Test Status

- `tests/integration/test_inv029_act_first_letter_cap.py` — 7/7 passing.
- Full suite — **5002 passed, 4 skipped, 0 failed** (parallel; 4995 baseline + 7
  new INV-029 tests; the 15 swept assertions stayed at parity count).
- `ruff check` on changed files — All checks passed. (`ruff format --check` flags
  only pre-existing legacy lines in `imm_commands.py`/`act.py` not touched here —
  left as-is to avoid unrelated churn.)

## Next Steps

Cross-file invariants remains the standing pass. Concrete next options:

1. **Close the INV-029 cousins** (now concrete + scoped, not vague candidates):
   the direct-f-string `act()` sites that bypass `act_format` and are still
   uncapped — **`do_say` / `do_tell`** (`mud/commands/communication.py` build
   `"{6$n says…"` / `"{k$n tells you…"`) and especially the **high-frequency
   combat damage messages** (`mud/combat/messages.py` / `engine.py` — e.g.
   `"the goblin misses you"` → ROM `"The goblin misses you"`). Close each by
   routing through `capitalize_act_line` with its own failing-first test. The
   wiznet `WIZ_PREFIX` `"{Z--> "` path is a lesser cousin (Python caps the inner
   message vs ROM's `buf[2]`=`-` no-op; prefix-on case only, unexercised).
2. **`VISION-002`** — dark-gate same-room divergence (`vision.py` vs
   `src/handler.c:2638`; `HANDLER_C_AUDIT.md`). Larger scope; write a failing
   test first. (Do NOT fold into the same session as the cousins.)
3. Fresh cross-file probe (affect ticks, position transitions, mob script triggers).

## Outstanding / carried-open

- **INV-029 cousins** (OPEN, tracked): `do_say`/`do_tell`, combat damage messages,
  wiznet `WIZ_PREFIX` path — see above + the INV-029 tracker row status cell.
- **`VISION-002`** (OPEN) — dark-gate same-room divergence.
- Known **xdist flakes**: `test_combat_death.py`, `test_backstab_uses_position_and_weapon`
  (pass in isolation, can flake under some parallel worker groupings); this
  session's full run had **0 failures**.
- pet-shop haggle / "now follows you" wrong-channel (INV-001 family, mailbox-only);
  `Character.pet` stale type annotation; `do_cast` object-targeting legs.

## Commit / push state

- This session: `7e9c488c` (INV-029 code) + the upcoming handoff-docs commit.
- **Local-only, NOT pushed** — await the user's say-so before pushing to
  `origin/master`. (`master` was in sync with `origin/master` at session start.)
