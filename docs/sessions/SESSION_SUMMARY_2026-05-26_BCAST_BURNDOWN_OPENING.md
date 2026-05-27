# Session Summary — 2026-05-26 — BCAST Class 1 burn-down opening (2.9.58)

## Headline

Class 1 BROADCAST_COVERAGE burn-down opened. Three real gaps closed
(BCAST-025 do_surrender, BCAST-012 do_invis, BCAST-011 do_incognito)
plus one false-positive row pair collapsed (BCAST-001/008 do_goto
covered by `_act_room` helper, helper-transitivity caveat).

## Commits (4 on master, ahead of `origin/master`)

| SHA | Gap(s) | File |
|-----|--------|------|
| `088a30e` | BCAST-025 | `mud/commands/combat.py:do_surrender` + new test |
| `74266c6` | BCAST-012 | `mud/commands/imm_display.py:do_invis` + new test |
| `1813e48` | BCAST-011 | `mud/commands/imm_display.py:do_incognito` + new test |
| (pending) | Chore: audit doc flips + version + CHANGELOG + session docs | — |

## Gaps closed

| ID | Bug | Pre-fix | Fix |
|----|-----|---------|-----|
| BCAST-025 | `do_surrender` only delivered TO_CHAR; opponent and bystanders silent | 0 broadcasts | Added TO_VICT "$n surrenders to you!" + TO_NOTVICT "$n tries to surrender to $N!" before `stop_fighting` |
| BCAST-012 | (a) toggle-off wording "fades back into existence" diverged from ROM "fades into existence"; (b) toggle-on broadcast silently dropped (invis_level set BEFORE `_act_room`, but `_act_room` enforces `can_see_character`); (c) level-set branch had no broadcast | 0 effective broadcasts | Fixed wording; re-ordered broadcast-before-commit on fade-out; added level-set broadcast |
| BCAST-011 | Toggle-off (uncloak) had no broadcast; level-set branch had no broadcast (toggle-on was correct because incognito does not hide in-room) | 1 broadcast (toggle-on only) | Added the two missing broadcasts |

## False positive collapsed

- **BCAST-001 / BCAST-008** (`@goto` / `do_goto`): audit flagged R=4 ROM
  acts vs Py=0 broadcast hits, but `do_goto` at
  `mud/commands/imm_commands.py:164` already broadcasts bamfout/bamfin
  via `_act_room` helper (lines 196, 198, 208, 210). The audit's
  body-only static scan didn't recognize `_act_room` as a broadcast
  helper. Audit-doc row reclassified to ✅ COVERED — **no code commit**,
  just bookkeeping.

## Helper-transitivity finding (load-bearing for future BCAST rows)

The `_act_room` helper at `mud/commands/imm_display.py:300-326` and
its `mud/commands/imm_commands.py:473-481` sibling both **enforce
`can_see_character(person, char)` per recipient**. For visibility-
transition broadcasts (fade-in/fade-out/cloak/uncloak), this means
the message gets silently dropped for any witness below the actor's
new `invis_level`/`incog_level` once that field is committed.

**Fix pattern**: emit the broadcast BEFORE committing the
visibility field on fade-out/cloak-on; emit AFTER for fade-in/uncloak
(when the field has just been cleared). This invariant should be
captured as an INV row if a third instance turns up. Candidate
INV identifier: `INV-024 VISIBILITY-TRANSITION-BROADCAST-ORDERING`.

## New integration tests (3 files, 7 cases)

- `tests/integration/test_surrender_broadcasts.py` (1)
- `tests/integration/test_invis_broadcasts.py` (3)
- `tests/integration/test_incognito_broadcasts.py` (3)

## Audit doc updates

`docs/parity/audits/BROADCAST_COVERAGE.md` rows flipped:

- Row 1 (`@goto`) → ✅ COVERED (false positive)
- Row 8 (`goto`) → ✅ COVERED (false positive)
- Row 11 (`incognito`) → ✅ FIXED (2.9.58), broadcast count 0 → 3
- Row 12 (`invis`) → ✅ FIXED (2.9.58), broadcast count 0 → 3
- Row 25 (`surrender`) → ✅ FIXED (2.9.58), broadcast count 0 → 2

Burn-down state: 4 of 29 ❌ rows resolved (3 fixed, 1 pair collapsed).
25 ❌ + 10 ⚠️ rows remain (plus the 209 ✅ baseline).

## Outstanding

1. **Combat-skill probe deferred**: BCAST-004 (`do_dirt`), BCAST-005
   (`do_disarm`), BCAST-026 (`do_trip`) all show R+V+N=2-3 ROM acts vs
   Py=0. The audit's hypothesis is they may route through `damage()` /
   `one_hit()` / the combat engine — **needs verification before
   promoting**. The combat skill functions in `mud/commands/combat.py`
   at lines 859/900/983 have NO inline `_act_room`/`act` calls in
   their bodies, so if the broadcasts are covered, they come from a
   deeper helper. Next session: read `mud/combat/engine.py`'s `damage`
   / `one_hit` and check whether the skill-specific TO_VICT/TO_NOTVICT
   strings ("$n shoves you backwards", "$n trips you", etc.) are
   emitted there. If not, they're real gap-closers (~2 broadcasts each).
2. **Door commands** (BCAST-003 close, BCAST-013 lock, BCAST-016 open,
   BCAST-027 unlock): SESSION_STATUS predicted these are likely covered
   by `mud/world/movement.py`. Same helper-transitivity probe — read
   the movement helper and check whether door state changes broadcast.
3. **Movement / position commands** (BCAST-006 enter, BCAST-021-024
   rest/sit/sleep/stand): these have large ROM act counts (5-12 per
   command). May be the most expensive remaining rows.
4. **INV-024 candidate**: VISIBILITY-TRANSITION-BROADCAST-ORDERING.
   Two instances surfaced this session (`do_invis` fade-out and the
   `_act_room` visibility filter). Track upstream — if a third
   instance appears, file as INV row.
5. **GitNexus reindex** still stale (last `069f17f`); now ~15 commits
   behind.
6. **Worktree hygiene** still pending from prior session (5 locked
   worktrees).
