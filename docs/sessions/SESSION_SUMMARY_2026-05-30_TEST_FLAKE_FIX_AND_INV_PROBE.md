# Session Summary — 2026-05-30 — Test Flake Fix and Invariant Probe

## Scope

Continued from `SESSION_SUMMARY_2026-05-30_DO_CAST_PK_GATES.md`.

Two-part session: (1) fixed the carried-open `test_combat_death.py` xdist
flake; (2) probed `Character.pet` type annotation and `add_follower` contract.

(1) The `test_combat_death.py` flake: `attack_round` was refactored in
FIGHT-019 to use `number_bits(5)` for the THAC0 hit roll, but 11 tests
still only monkeypatched `number_percent` and `number_range`. The
unpatched `number_bits(5)` call produced nondeterministic results under
xdist, causing `assert victim not in room.people` failures when the hit
roll missed. Fix: added `monkeypatch.setattr("mud.utils.rng_mm.number_bits",
lambda bits: 19)` (ROM auto-hit value) to all 11 `attack_round`-using
tests that lacked it.

(2) Probed `add_follower` ROM C contract (`src/act_comm.c:1591-1608`) vs
Python (`mud/characters/follow.py`). ROM calls `bug()` and returns on
`ch->master != NULL`; Python calls `stop_follower` then continues. This is
a deliberate defensive divergence (all callers ensure pre-null master), not
a parity bug. Also probed `Character.pet` type annotation: typed as
`Character | None` but always set to `MobInstance | None`. Not a behavioral
bug (Python doesn't enforce types at runtime), so noted for future type
hygiene rather than filed as an INV.

## Outcome

### Test stabilization — ✅ FIXED (2.11.54)

- **Python**: `tests/test_combat_death.py` — 11 tests gained
  `number_bits(bits: 19)` monkeypatch to guarantee `attack_round` always
  hits under the ROM THAC0 model
- **Root cause**: FIGHT-019 replaced the legacy `number_percent()` hit
  model with `number_bits(5)` THAC0, but the test patches were not updated
- **Tests**: 23/23 passing (all green, including the previously-flaky
  `test_raw_kill_awards_group_xp_and_creates_corpse`)

### Probe: `add_follower` / `Character.pet` — no gap filed

- `add_follower` Python diverges from ROM (stops old follower vs ROM's
  `bug()`+return), but all callers ensure pre-null master; defensive
  divergence, not a parity bug
- `Character.pet: Character | None` should be `MobInstance | None` for
  accuracy; not a behavioral issue (noted for future type hygiene pass)

## Files Modified

- `tests/test_combat_death.py` — added `number_bits` monkeypatch to 11
  `attack_round`-using tests
- `CHANGELOG.md` — added 2.11.54 unreleased entry
- `pyproject.toml` — bumped `2.11.53` → `2.11.54`

## Verification

- `pytest tests/test_combat_death.py -n0 -v` — 23 passed
- `pytest tests/test_combat_death.py -n auto -q` — 23 passed
  (previously flaky under xdist)
- `ruff check tests/test_combat_death.py` — all checks passed
- `gitnexus_detect_changes` — low risk, 0 affected processes

## Outstanding

- Continue cross-file invariant probe/close cycle.
- `Character.pet` type annotation hygiene (`Character | None` →
  `MobInstance | None`) — future type pass, not a parity bug.
- Per-spell handler Object branches (bless/curse/poison/remove_curse/
  invisibility) still deferred to future per-spell audit work.
- `test_backstab_uses_position_and_weapon` carried-open xdist flake
  (separate RNG dependency, not `number_bits`-related).