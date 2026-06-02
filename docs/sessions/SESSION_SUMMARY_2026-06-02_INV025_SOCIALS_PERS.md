# Session Summary — 2026-06-02 — INV-025 socials `$n` PERS class CLOSED (2.12.56)

## Goal

Close the last open item in the INV-025 (MOBPROG-ACT-TRIGGER-DISPATCH /
per-recipient PERS) sweep: the **socials `$n`-baking room-broadcast class** in
`mud/commands/socials.py`, flagged as the next intended task by the prior
session.

## What landed

One commit, **2.12.56 / `145a87ad`** (local, not pushed):

### The divergence

`perform_social` rendered every ROM `act()` social line by baking the actor
name once and broadcasting one string to all recipients:

```python
char.room.broadcast(expand_placeholders(social.others_found, char, victim), exclude=char)
victim.messages.append(expand_placeholders(social.vict_found, char, victim))
```

Three faults against ROM `check_social` (`src/interp.c:634-685`):

1. **No per-recipient PERS masking.** `expand_placeholders` replaces
   `$n`→`actor.name` with no `can_see` gate, so an invisible socialer leaked
   its name to witnesses without detect-invis (INV-027).
2. **No TRIG_ACT dispatch.** NPC bystanders never received
   `mp_act_trigger(..., TRIG_ACT)` for the social line (INV-025's primary
   contract).
3. **TO_NOTVICT vs TO_ROOM bug (behavioral).** ROM
   `act(others_found, ch, NULL, victim, TO_NOTVICT)` (`src/interp.c:648`)
   excludes the **victim**, who receives only `vict_found` (`TO_VICT`). The
   Python `broadcast(exclude=char)` is TO_ROOM — it delivered `others_found` to
   the victim too, so the victim saw both lines.

### The fix

- Room broadcasts → shared `act_to_room` helper (per-recipient PERS via
  `act_format` + TRIG_ACT): `others_no_arg`/`others_auto` as TO_ROOM,
  `others_found` as TO_NOTVICT (`exclude=victim`), and the NPC auto-react
  echo/slap broadcasts (actor/victim swapped, `exclude=char`).
- Directed lines → new module-local `socials._act_to_char` helper: render via
  `act_format` (PERS), deliver via single-delivery `push_message`, dispatch
  TRIG_ACT to NPC recipients. Covers `char_no_arg`/`char_auto`/`char_found`
  (TO_CHAR), `vict_found` (TO_VICT), the echo/slap directed lines, and the
  "They aren't here." not-found literal (now on the single-delivery channel).
- Mirrors ROM `act_new` (`src/comm.c:2230-2385`) per-recipient logic.
- `expand_placeholders` (in `mud/models/social.py`) is **retained** — it still
  has a production caller in `mud/commands/imc.py:308` (so not orphaned).

### Tests

- New `tests/integration/test_inv025_socials_pers_sweep.py`:
  - `test_others_no_arg_masks_invisible_actor` — invisible actor renders
    "Someone wibbles." to an observer (not "Alice").
  - `test_targeted_social_excludes_victim_from_notvict` — victim receives
    exactly `["Alice wibbles at you."]` (vict_found only), observer gets
    others_found.
- Flipped `test_socials.py::test_social_with_target_excludes_actor_from_broadcast`
  from the bug-encoding `len(bob.messages) == 2` to ROM-correct
  `bob.messages == ["Alice smiles at you."]` with an `interp.c:648` citation
  (the AGENTS.md "test asserts behavior contradicting ROM C" case).

## Verification

- `tests/integration/test_inv025_socials_pers_sweep.py` +
  `test_socials.py` + `test_social_placeholders.py` + `test_runtime_models.py`:
  45 passed.
- Social/mobprog `-k` surface: 131 passed.
- Full `tests/integration/`: 2735 passed, 3 skipped.
- `ruff check` clean on touched files.
- `gitnexus_detect_changes`: low risk, scope exactly = `perform_social` +
  tracker doc + flipped test. No unexpected affected processes.

## Docs / trackers updated

- `docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` — INV-025 row: socials class
  marked CLOSED, "Touched by: `mud/commands/socials.py`", test added to the
  enforcement-test list.
- `CHANGELOG.md` — new `### Fixed` bullet under `[Unreleased]`.
- `pyproject.toml` — version 2.12.55 → 2.12.56 (patch: parity gap closure).

## Outstanding

No known open items in the INV-025 `$n`-broadcast class. The sweep across
`mud/commands/`, `mud/combat/`, `mud/world/`, `mud/skills/`, and socials is
complete. Next cross-file-invariants candidates (probe-then-scope): mob script
trigger ordering, position transitions, group/follower chains.

**Filed mid-session (out of scope, NOT fixed here):**

- **INTERP-025** (`docs/parity/INTERP_C_AUDIT.md`) — self-targeted socials are
  unreachable. ROM `get_char_room` (`src/handler.c:2194`) returns `ch` for
  `"self"` and does not skip `ch` in its room-people loop, so `smile self` /
  `smile <ownname>` → `victim == ch` → `char_auto`/`others_auto`. Python's
  victim search does `if person is char: continue` and has no `"self"` keyword,
  so those fall through to "They aren't here." and the `char_auto`/`others_auto`
  branch is dead code. Pre-existing; surfaced during the 2.12.56 conversion.
  When closed, `test_socials.py::test_social_targeting_self` (which currently
  asserts the buggy not-found behavior) must flip.

**Push note:** 2.12.49–56 are committed locally but NOT yet pushed; 2.12.48 is
the last on `master`.
